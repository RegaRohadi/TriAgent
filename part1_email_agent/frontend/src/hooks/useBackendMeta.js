import { useEffect, useState } from "react";
import { api } from "../api.js";

export function useBackendMeta() {
  const [meta, setMeta] = useState("loading…");
  const [companionPorts, setCompanionPorts] = useState({});
  const [samples, setSamples] = useState([]);

  useEffect(() => {
    api
      .health()
      .then((h) => {
        setCompanionPorts(h.companions || {});
        setMeta(
          `Rega's Support desk · llm: ${h.llm_backend} · embeddings: ${h.embedding_backend} · knowledge base: ${h.kb_chunks} chunks from ${h.kb_documents.length} documents`
        );
      })
      .catch(() => setMeta("backend unavailable"));
    api.samples().then(setSamples).catch(() => setSamples([]));
  }, []);

  return { meta, companionPorts, samples };
}
