"use client";

/**
 * EditorStepType — editor-responsive-redesign PDCA (#3, Step 4).
 *
 * Mobile wizard step 1: post-type selection. Thin wrapper around
 * PostTypeSelector with a small intro paragraph; the role-gating hint is
 * rendered by PostTypeSelector itself.
 *
 * Pattern source: design §4.1 (EditorStepType).
 */

import { useI18n } from "@/i18n";
import type { ApiUser } from "@/lib/api";
import {
  PostTypeSelector,
  type ArtistApplicationStatus,
} from "@/components/post-editor/PostTypeSelector";

export interface EditorStepTypeProps {
  type: "general" | "product";
  onTypeChange: (v: "general" | "product") => void;
  userRole: ApiUser["role"] | undefined;
  applicationStatus: ArtistApplicationStatus | undefined;
  disabled?: boolean;
}

export function EditorStepType({
  type,
  onTypeChange,
  userRole,
  applicationStatus,
  disabled,
}: EditorStepTypeProps) {
  const { t } = useI18n();
  return (
    <section className="space-y-4">
      <header className="space-y-1">
        <h2 className="text-base font-semibold">
          {t("post.editor.wizard.stepType.title")}
        </h2>
        <p className="text-xs text-text-muted">
          {t("post.editor.wizard.stepType.hint")}
        </p>
      </header>
      <PostTypeSelector
        value={type}
        onChange={onTypeChange}
        userRole={userRole}
        applicationStatus={applicationStatus}
        disabled={disabled}
      />
    </section>
  );
}
