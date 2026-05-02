"use client";

/**
 * EditorStepProductMeta — editor-responsive-redesign PDCA (#3, Step 4).
 *
 * Mobile wizard step 3 (only when type === "product"): wraps the existing
 * ProductFields component in a wizard-friendly container with a heading.
 *
 * #7 editor-product-meta PDCA will swap ProductFields for a structured-input
 * variant; this wrapper stays stable so the wizard layout doesn't change.
 *
 * Pattern source: design §4.1 (EditorStepProductMeta).
 */

import { useI18n } from "@/i18n";
import {
  ProductFields,
  type ProductFieldsProps,
} from "@/components/post-editor/ProductFields";

export type EditorStepProductMetaProps = ProductFieldsProps;

export function EditorStepProductMeta(props: EditorStepProductMetaProps) {
  const { t } = useI18n();
  return (
    <section className="space-y-4">
      <header className="space-y-1">
        <h2 className="text-base font-semibold">
          {t("post.editor.wizard.stepProductMeta.title")}
        </h2>
        <p className="text-xs text-text-muted">
          {t("post.editor.wizard.stepProductMeta.hint")}
        </p>
      </header>
      <ProductFields {...props} />
    </section>
  );
}
