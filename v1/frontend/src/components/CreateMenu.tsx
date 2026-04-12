"use client";

import Link from "next/link";
import { useEffect, useId, useRef, useState } from "react";

type CreateMenuProps = {
  trigger: (opts: {
    open: boolean;
    toggle: () => void;
    triggerProps: {
      "aria-expanded": boolean;
      "aria-haspopup": "menu";
      "aria-controls": string;
    };
  }) => React.ReactNode;
  align?: "top" | "bottom";
  side?: "left" | "right";
};

type MenuItem = {
  href: string;
  icon: string;
  iconBg: string;
  title: string;
  subtitle: string;
};

const ITEMS: MenuItem[] = [
  {
    href: "/posts/new?type=product",
    icon: "🎨",
    iconBg: "bg-primary/15 text-primary",
    title: "작품 등록",
    subtitle: "판매 · 경매 · 블루버드 후원",
  },
  {
    href: "/posts/new?type=general",
    icon: "✏️",
    iconBg: "bg-surface-hover",
    title: "일반 포스트",
    subtitle: "작업 과정 · 생각 · 사진",
  },
];

export function CreateMenu({
  trigger,
  align = "top",
  side = "left",
}: CreateMenuProps) {
  const [open, setOpen] = useState(false);
  const [focusIdx, setFocusIdx] = useState<number>(-1);
  const ref = useRef<HTMLDivElement>(null);
  const itemRefs = useRef<Array<HTMLAnchorElement | null>>([]);
  const menuId = useId();

  useEffect(() => {
    if (!open) {
      setFocusIdx(-1);
      return;
    }
    const onClick = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    window.addEventListener("mousedown", onClick);
    return () => window.removeEventListener("mousedown", onClick);
  }, [open]);

  useEffect(() => {
    if (open && focusIdx >= 0) {
      itemRefs.current[focusIdx]?.focus();
    }
  }, [open, focusIdx]);

  const close = () => setOpen(false);

  function handleKeyDown(e: React.KeyboardEvent) {
    if (!open) return;
    if (e.key === "Escape") {
      e.preventDefault();
      setOpen(false);
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setFocusIdx((i) => (i + 1) % ITEMS.length);
      return;
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      setFocusIdx((i) => (i <= 0 ? ITEMS.length - 1 : i - 1));
      return;
    }
    if (e.key === "Home") {
      e.preventDefault();
      setFocusIdx(0);
      return;
    }
    if (e.key === "End") {
      e.preventDefault();
      setFocusIdx(ITEMS.length - 1);
      return;
    }
  }

  const toggle = () => {
    setOpen((v) => {
      const next = !v;
      if (next) setFocusIdx(0);
      return next;
    });
  };

  const menuPos = align === "top" ? "bottom-full mb-2" : "top-full mt-2";
  const sidePos = side === "left" ? "left-0" : "right-0";

  return (
    <div ref={ref} className="relative" onKeyDown={handleKeyDown}>
      {trigger({
        open,
        toggle,
        triggerProps: {
          "aria-expanded": open,
          "aria-haspopup": "menu",
          "aria-controls": menuId,
        },
      })}

      {open && (
        <div
          id={menuId}
          role="menu"
          aria-label="작성 메뉴"
          className={`absolute ${menuPos} ${sidePos} w-64 card p-2 z-40 shadow-xl`}
        >
          {ITEMS.map((item, idx) => (
            <Link
              key={item.href}
              ref={(el) => {
                itemRefs.current[idx] = el;
              }}
              href={item.href}
              onClick={close}
              role="menuitem"
              tabIndex={focusIdx === idx ? 0 : -1}
              className="flex items-start gap-3 p-3 rounded-lg hover:bg-surface-hover focus:bg-surface-hover focus:outline-none focus:ring-2 focus:ring-primary transition-colors"
            >
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center text-xl flex-shrink-0 ${item.iconBg}`}
              >
                {item.icon}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-semibold text-text-primary">
                  {item.title}
                </div>
                <div className="text-xs text-text-muted mt-0.5">
                  {item.subtitle}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
