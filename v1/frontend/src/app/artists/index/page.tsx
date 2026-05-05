import type { Metadata } from "next";
import { ArtistIndexClient } from "./ArtistIndexClient";

export const metadata: Metadata = {
  title: "글로벌 신진작가 인덱스 | Domo Lounge",
  description:
    "Domo 글로벌 신진작가 인덱스 — 전 세계에서 활동 중인 신진 작가들의 실시간 랭킹",
  openGraph: {
    title: "Domo 글로벌 신진작가 인덱스",
    description:
      "전 세계에서 떠오르는 신진 작가들의 실시간 랭킹을 확인하세요.",
    type: "website",
  },
};

export default function ArtistIndexPage() {
  return <ArtistIndexClient />;
}
