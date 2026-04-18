import { HistoryEntry, RepresentativeWork } from "@/lib/api";

export type ApplicationFormData = {
  // Step 1
  school: string;
  department: string;
  graduation_year: number;
  is_enrolled: boolean;
  genre_tags: string[];
  edu_email: string;
  edu_email_verified: boolean;

  // Step 2
  representative_works: RepresentativeWork[];

  // Step 3
  statement: string;
  enrollment_proof_url: string;
  portfolio_urls: string;
  intro_video_url: string;

  // Step 4
  exhibitions: HistoryEntry[];
  awards: HistoryEntry[];
};

export interface StepProps {
  data: ApplicationFormData;
  onChange: (partial: Partial<ApplicationFormData>) => void;
}

export const GENRES = [
  "painting",
  "drawing",
  "photography",
  "sculpture",
  "mixed_media",
  "digital",
  "installation",
];
