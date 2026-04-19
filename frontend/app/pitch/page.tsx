import type { Metadata } from "next";
import PitchClient from "../../components/pitch/PitchClient";

export const metadata: Metadata = {
  title: "DepScope — 60s Animated Pitch",
  description:
    "Package Intelligence for AI Agents, explained in 60 seconds.",
  robots: { index: false, follow: false },
};

export default function PitchPage() {
  return <PitchClient />;
}
