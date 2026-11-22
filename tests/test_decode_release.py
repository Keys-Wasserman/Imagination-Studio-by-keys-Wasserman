"""The optional H3 release sits after sampling and before both decoders."""

import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "spark"))
import spark_generate as sg  # noqa: E402


def test_decode_release_graph_is_opt_in_and_orders_both_decoders(monkeypatch):
    graph = {"13": {"inputs": {"samples": ["12", 0]}},
             "14": {"inputs": {"samples": ["12", 0]}}}
    sg.release_before_decode(graph, False)
    assert "98" not in graph
    monkeypatch.setattr(sg, "call", lambda path: {"StudioDecodeRelease": {"input": {}}})
    sg.release_before_decode(graph, True)
    assert graph["98"]["inputs"]["samples"] == ["12", 0]
    assert graph["13"]["inputs"]["samples"] == ["98", 0]
    assert graph["14"]["inputs"]["samples"] == ["98", 0]


def test_decode_release_node_keeps_latent_and_unloads_in_order(monkeypatch):
    calls = []
    management = types.ModuleType("comfy.model_management")
    management.unload_all_models = lambda: calls.append("unload")
    management.soft_empty_cache = lambda: calls.append("cache")
    comfy = types.ModuleType("comfy")
    comfy.model_management = management
    monkeypatch.setitem(sys.modules, "comfy", comfy)
    monkeypatch.setitem(sys.modules, "comfy.model_management", management)
    engine = types.ModuleType("studio_test_h3_engine")
    engine.release = lambda: calls.append("engine")
    blocks = type("TensorFoldH3Blocks", (), {})
    blocks.__module__ = engine.__name__
    nodes = types.ModuleType("nodes")
    nodes.NODE_CLASS_MAPPINGS = {"TensorFoldH3Blocks": blocks}
    monkeypatch.setitem(sys.modules, "nodes", nodes)
    monkeypatch.setitem(sys.modules, engine.__name__, engine)
    path = ROOT / "spark/studio_decode_cleanup/__init__.py"
    spec = importlib.util.spec_from_file_location("studio_decode_cleanup", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    latent = {"samples": object()}
    assert module.StudioDecodeRelease().release(latent) == (latent,)
    assert calls == ["unload", "engine", "cache"]
    calls.clear()
    nodes.NODE_CLASS_MAPPINGS.clear()
    assert module.StudioDecodeRelease().release(latent) == (latent,)
    assert calls == ["unload", "cache"]
