(() => {
  const views = {
    pitch: document.getElementById("view-pitch"),
    thinking: document.getElementById("view-thinking"),
    verdict: document.getElementById("view-verdict"),
    file: document.getElementById("view-file"),
    archive: document.getElementById("view-archive"),
  };

  const pitchForm = document.getElementById("pitch-form");
  const pitchInput = document.getElementById("pitch-input");
  const checkBtn = document.getElementById("check-btn");
  const micBtn = document.getElementById("mic-btn");
  const pitchStatus = document.getElementById("pitch-status");
  const thinkingDetail = document.getElementById("thinking-detail");
  const verdictCard = document.getElementById("verdict-card");
  const reactionLine = document.getElementById("reaction-line");
  const matchBlock = document.getElementById("match-block");
  const nomatchBlock = document.getElementById("nomatch-block");
  const pastIdea = document.getElementById("past-idea");
  const archiveQuote = document.getElementById("archive-quote");
  const verdictWhy = document.getElementById("verdict-why");
  const feedbackRow = document.getElementById("feedback-row");
  const feedbackStatus = document.getElementById("feedback-status");
  const archiveSearch = document.getElementById("archive-search");
  const archiveList = document.getElementById("archive-list");
  const archiveMeta = document.getElementById("archive-meta");
  const rejectForm = document.getElementById("reject-form");
  const rejectIdea = document.getElementById("reject-idea");
  const rejectDiscussion = document.getElementById("reject-discussion");
  const rejectBtn = document.getElementById("reject-btn");
  const rejectStatus = document.getElementById("reject-status");
  const rejectResult = document.getElementById("reject-result");
  const rejectSummary = document.getElementById("reject-summary");
  const rejectReason = document.getElementById("reject-reason");

  let lastResult = null;
  let mediaRecorder = null;
  let mediaChunks = [];
  let recording = false;
  let checkController = null;

  function showView(name) {
    Object.entries(views).forEach(([key, el]) => {
      el.classList.toggle("is-active", key === name);
    });
    if (name === "archive") loadArchive(archiveSearch.value.trim());
    if (name === "pitch") pitchInput.focus();
  }

  document.querySelectorAll("[data-go]").forEach((btn) => {
    btn.addEventListener("click", () => showView(btn.dataset.go));
  });

  function setStatus(el, text) {
    if (!text) {
      el.hidden = true;
      el.textContent = "";
      return;
    }
    el.hidden = false;
    el.textContent = text;
  }

  async function runCheck(pitch) {
    if (checkController) checkController.abort();
    checkController = new AbortController();
    const timeout = setTimeout(() => checkController.abort(), 90000);

    showView("thinking");
    thinkingDetail.textContent = "Speculating failure mode";
    const stages = [
      "Speculating failure mode",
      "Searching rejection reasons",
      "Judging shared flaw",
    ];
    let i = 0;
    const tick = setInterval(() => {
      i = (i + 1) % stages.length;
      thinkingDetail.textContent = stages[i];
    }, 1400);

    try {
      const res = await fetch("/api/check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pitch }),
        signal: checkController.signal,
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || `Check failed (${res.status})`);
      if ("score" in (data.match || {}) || "score" in (data.raw_top_match || {})) {
        console.warn("API returned a score field; UI intentionally ignores it.");
      }
      lastResult = data;
      renderVerdict(data);
    } catch (err) {
      const msg =
        err.name === "AbortError"
          ? "Timed out waiting for the archive — try again."
          : err.message || "Something went wrong.";
      setStatus(pitchStatus, msg);
      showView("pitch");
    } finally {
      clearInterval(tick);
      clearTimeout(timeout);
      checkController = null;
    }
  }

  function renderVerdict(data) {
    verdictCard.classList.remove("is-revealed", "is-match", "is-clear");
    setStatus(feedbackStatus, "");
    feedbackRow.querySelectorAll("button").forEach((b) => {
      b.disabled = false;
    });

    reactionLine.textContent = data.reviewer_line || "";
    verdictWhy.textContent = data.verdict_why || "";

    if (data.match) {
      matchBlock.hidden = false;
      nomatchBlock.hidden = true;
      pastIdea.textContent = data.match.idea_summary || "";
      archiveQuote.textContent = data.match.rejection_reason || "";
      verdictCard.classList.add("is-match");
    } else {
      matchBlock.hidden = true;
      nomatchBlock.hidden = false;
      verdictCard.classList.add("is-clear");
    }

    showView("verdict");
    void verdictCard.offsetWidth;
    verdictCard.classList.add("is-revealed");
  }

  pitchForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const pitch = pitchInput.value.trim();
    if (!pitch) return;
    if (pitch.length < 8) {
      setStatus(pitchStatus, "Add a bit more detail — one short sentence is enough.");
      return;
    }
    setStatus(pitchStatus, "");
    checkBtn.disabled = true;
    runCheck(pitch).finally(() => {
      checkBtn.disabled = false;
    });
  });

  feedbackRow.addEventListener("click", async (e) => {
    const btn = e.target.closest("[data-feedback]");
    if (!btn || !lastResult) return;
    const wasReal = btn.dataset.feedback === "true";
    feedbackRow.querySelectorAll("button").forEach((b) => {
      b.disabled = true;
    });
    try {
      const res = await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          new_idea: lastResult.new_idea,
          speculated_flaw: lastResult.speculated_flaw,
          match: lastResult.match,
          raw_top_match: lastResult.raw_top_match,
          was_real_match: wasReal,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || "Could not save feedback");
      setStatus(
        feedbackStatus,
        wasReal ? "Logged as a fair call." : "Logged as not the same thing."
      );
    } catch (err) {
      setStatus(feedbackStatus, err.message || "Feedback failed.");
      feedbackRow.querySelectorAll("button").forEach((b) => {
        b.disabled = false;
      });
    }
  });

  async function loadArchive(q = "") {
    archiveMeta.textContent = "Loading…";
    archiveList.innerHTML = "";
    try {
      const url = q ? `/api/archive?q=${encodeURIComponent(q)}` : "/api/archive";
      const res = await fetch(url);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || "Could not load archive");
      archiveMeta.textContent =
        data.count === 0
          ? "No rejections on file."
          : `${data.count} stored rejection${data.count === 1 ? "" : "s"}`;
      archiveList.innerHTML = (data.items || [])
        .map(
          (item, idx) => `
        <li style="animation-delay: ${Math.min(idx * 40, 320)}ms">
          <p class="idea">${escapeHtml(item.idea_summary || "")}</p>
          <p class="reason">${escapeHtml(item.rejection_reason || "")}</p>
        </li>`
        )
        .join("");
    } catch (err) {
      archiveMeta.textContent = err.message || "Archive unavailable.";
    }
  }

  let searchTimer = null;
  archiveSearch.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => loadArchive(archiveSearch.value.trim()), 180);
  });

  function escapeHtml(str) {
    return String(str)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  async function toggleMic() {
    if (recording) {
      mediaRecorder?.stop();
      return;
    }

    if (!navigator.mediaDevices?.getUserMedia) {
      setStatus(pitchStatus, "Microphone not available in this browser.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaChunks = [];
      const mime = MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : undefined;
      mediaRecorder = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) mediaChunks.push(e.data);
      };
      mediaRecorder.onstop = async () => {
        recording = false;
        micBtn.setAttribute("aria-pressed", "false");
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(mediaChunks, { type: mediaRecorder.mimeType || "audio/webm" });
        await transcribeBlob(blob);
      };
      mediaRecorder.start();
      recording = true;
      micBtn.setAttribute("aria-pressed", "true");
      setStatus(pitchStatus, "Listening… click Mic again to stop.");
    } catch (err) {
      setStatus(pitchStatus, "Microphone permission denied.");
    }
  }

  async function transcribeBlob(blob) {
    setStatus(pitchStatus, "Transcribing…");
    const body = new FormData();
    body.append("audio", blob, "pitch.webm");
    try {
      const res = await fetch("/api/transcribe", { method: "POST", body });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || "Transcription failed");
      if (!data.text) throw new Error("Nothing transcribed — try again.");
      pitchInput.value = data.text;
      setStatus(pitchStatus, "Transcribed. Edit if needed, then check.");
    } catch (err) {
      if (await tryBrowserSpeech()) return;
      setStatus(pitchStatus, err.message || "Could not transcribe audio.");
    }
  }

  function tryBrowserSpeech() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return Promise.resolve(false);
    return new Promise((resolve) => {
      const rec = new SpeechRecognition();
      rec.lang = "en-US";
      rec.interimResults = false;
      rec.onresult = (event) => {
        const text = event.results[0][0].transcript;
        pitchInput.value = text;
        setStatus(pitchStatus, "Transcribed via browser speech. Edit if needed.");
        resolve(true);
      };
      rec.onerror = () => resolve(false);
      setStatus(pitchStatus, "Trying browser speech… speak now.");
      rec.start();
    });
  }

  micBtn.addEventListener("click", toggleMic);

  rejectForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const idea = rejectIdea.value.trim();
    const discussion = rejectDiscussion.value.trim();
    if (!idea || !discussion) return;
    setStatus(rejectStatus, "Extracting reason and embedding…");
    rejectResult.hidden = true;
    rejectBtn.disabled = true;
    try {
      const res = await fetch("/api/reject", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ idea, discussion }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || `Save failed (${res.status})`);
      rejectSummary.textContent = data.idea_summary || idea;
      rejectReason.textContent = data.rejection_reason || discussion;
      rejectResult.hidden = false;
      setStatus(rejectStatus, "Filed to the archive.");
      rejectIdea.value = "";
      rejectDiscussion.value = "";
    } catch (err) {
      setStatus(rejectStatus, err.message || "Could not file rejection.");
    } finally {
      rejectBtn.disabled = false;
    }
  });

  pitchInput.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      pitchForm.requestSubmit();
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") showView("pitch");
  });
})();
