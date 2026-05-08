import { useState, useCallback } from "react";
import {
  adminListDiversityConfigs,
  adminPatchDiversityConfig,
  DiversityConfigOut,
  DiversityConfigPatch,
} from "@/lib/api";

export function useDiversityConfig() {
  const [configs, setConfigs] = useState<DiversityConfigOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [patching, setPatching] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await adminListDiversityConfigs();
      setConfigs(data);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "다양성 설정을 불러오지 못했습니다.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  const patch = useCallback(
    async (name: string, body: DiversityConfigPatch): Promise<DiversityConfigOut> => {
      setPatching(true);
      try {
        const updated = await adminPatchDiversityConfig(name, body);
        setConfigs((prev) =>
          prev.map((c) => (c.name === name ? updated : c))
        );
        return updated;
      } finally {
        setPatching(false);
      }
    },
    []
  );

  const feedDefault = configs.find((c) => c.name === "feed_default") ?? null;

  return {
    configs,
    feedDefault,
    loading,
    error,
    load,
    patch,
    patching,
  };
}
