"use strict";
/* Optional, local rea-video analysis of a clip already in the Studio Library. */
const REA = { status: null, loading: false, open: null, audio: false, job: null };
async function reaLoad() {
  if (REA.status || REA.loading) return;
  REA.loading = true;
  try { REA.status = await api("/api/rea-video"); }
  catch (e) { REA.status = { ready: false, why: e.message === "Not Found"
    ? "Studio's running server has not loaded video breakdowns yet. Let the current render finish, then restart Studio and check again."
    : e.message }; }
  REA.loading = false;
  if (tab === "Library") render();
}
function reaButtons(m) {
  if (m.kind !== "video") return [];
  return [el("button", { class: "small", title: "Find shots, cuts, pacing and how this clip may have been made",
    onclick: () => { REA.open = m.path; REA.audio = false; REA.job = null; render();
      setTimeout(() => document.querySelector("#reapanel")?.scrollIntoView({ behavior: "smooth", block: "start" }), 60); } }, "Break down")];
}
function reaPanel() {
  if (!REA.open) return null;
  const state = REA.status || { ready: false, why: "Checking the optional analyzer…" };
  const recent = REA.job ? jobs.find(j => j.id === REA.job) :
    [...jobs].reverse().find(j => j.kind === "rea_video" && (j.params?.video || "").endsWith("/" + REA.open));
  const source = REA.open;
  return el("section", { class: "card", id: "reapanel", style: "margin:12px 0" },
    el("div", { class: "row" }, el("h3", { class: "fit" }, "Break down a video"),
      el("button", { class: "small", onclick: () => { REA.open = null; render(); } }, "Close")),
    el("p", { class: "note" }, source),
    el("p", { class: "note" }, "rea-video finds shot boundaries, visual evidence, pacing and a remake outline. It runs locally through Studio's queue and writes VIDEO.md plus a report package. It does not render a new clip or send this video to a vision service."),
    !state.ready ? el("div", { class: "row", style: "align-items:center" },
      el("p", { class: "note fit", style: "color:var(--warn)" }, state.why),
      el("button", { class: "small", onclick: () => { REA.status = null; reaLoad(); } }, "Check again")) : null,
    el("label", { style: "display:flex;gap:6px;align-items:center" },
      bind(REA, "audio", el("input", { type: "checkbox", style: "width:auto" })),
      "Separate voice, music and effects (first run downloads about 216 MB of models)"),
    el("button", { class: "hot", disabled: !state.ready, onclick: async () => { try {
      const job = await api("/api/jobs", { kind: "rea_video", title: "Break down " + source.split("/").pop(), params: { video: source, audio: REA.audio } });
      REA.job = job.id; await poll(); render();
    } catch (e) { toast(e.message); } } }, "Queue breakdown"),
    recent ? el("div", { style: "margin-top:12px" }, jobCard(recent),
      recent.status === "done" ? el("div", { class: "row", style: "margin-top:8px" },
        el("a", { class: "fit", href: file(recent.outputs[0]), target: "_blank", rel: "noopener" }, "Read VIDEO.md"),
        el("a", { class: "fit", href: file(recent.outputs[1]), download: "rea-video-report.zip" }, "Download full report")) : null) : null);
}

function reaLibrary() {
  const reports = [...jobs].filter(j => j.kind === "rea_video" && j.status === "done" && j.outputs?.length === 2).reverse();
  if (!reports.length) return null;
  return el("section", { class: "card", style: "margin:12px 0" }, el("h3", {}, "Video breakdowns"),
    reports.map(j => el("div", { class: "row", style: "margin:6px 0" },
      el("span", { class: "fit" }, j.title),
      el("a", { class: "small", href: file(j.outputs[0]), target: "_blank", rel: "noopener" }, "VIDEO.md"),
      el("a", { class: "small", href: file(j.outputs[1]), download: "rea-video-report.zip" }, "Full report"))));
}
