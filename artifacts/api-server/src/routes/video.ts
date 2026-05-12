import { Router } from "express";
import { createVideoJob, getJob } from "../services/videoGenerator";

const router = Router();

router.post("/video/generate", async (req, res) => {
  const { text } = req.body as { text?: string };
  if (!text || text.trim().length < 10) {
    res.status(400).json({ error: "Text is required (min 10 chars)" });
    return;
  }
  const jobId = await createVideoJob(text.trim());
  res.json({ jobId, status: "pending" });
});

router.get("/video/status/:id", (req, res) => {
  const job = getJob(req.params["id"]!);
  if (!job) {
    res.status(404).json({ error: "Job not found" });
    return;
  }
  res.json({ id: job.id, status: job.status, error: job.error });
});

export default router;
