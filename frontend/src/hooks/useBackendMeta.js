import { useEffect, useState } from "react";
import { api } from "../api.js";

export function useBackendMeta() {
  const [meta, setMeta] = useState("loading…");
  const [samples, setSamples] = useState([]);

  useEffect(() => {
    api
      .health()
      .then((h) => {
        setMeta(
          `Nimbus Cloud support desk · llm: ${h.llm_backend}${h.llm_model ? `/${h.llm_model}` : ""} · embeddings: ${h.embedding_backend} · knowledge base: ${h.kb_chunks} chunks from ${h.kb_documents.length} documents`,
        );
      })
      .catch(() => setMeta("backend unavailable"));
    api.samples().then(setSamples).catch(() => setSamples([]));
  }, []);

  return { meta, samples };
}
