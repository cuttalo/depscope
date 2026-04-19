import type { Metadata } from "next";
import { LegalLayout, Sec, Strong, A } from "../../components/legal/LegalLayout";

export const metadata: Metadata = {
  title: "Imprint — DepScope",
  description:
    "Legal disclosures for DepScope as required by art. 7 D.Lgs. 70/2003 (Italy).",
  alternates: {
    canonical: "https://depscope.dev/imprint",
    languages: {
      en: "https://depscope.dev/imprint",
      "zh-CN": "https://depscope.dev/zh/imprint",
      "x-default": "https://depscope.dev/imprint",
    },
  },
};

export default function ImprintPage() {
  return (
    <LegalLayout title="Imprint" updated="April 19, 2026">
      <Sec id="company" title="Company">
        <p>
          <Strong>Cuttalo srl</Strong>
          <br />
          Registered office: Italy
          <br />
          VAT / P.IVA: <Strong>IT03242390734</Strong>
          <br />
          General contact:{" "}
          <A href="mailto:depscope@cuttalo.com">depscope@cuttalo.com</A>
        </p>
        <p className="mt-2 text-xs">
          These disclosures are provided pursuant to art. 7 D.Lgs. 9 April
          2003, n. 70 (Italian e-commerce law) and art. 2250 of the Italian
          Civil Code. Full registry details (REA, PEC) are available on
          request.
        </p>
      </Sec>

      <Sec id="representative" title="Legal representative">
        <p>The company&apos;s legal representative is indicated in the Italian business registry.</p>
      </Sec>

      <Sec id="contacts" title="Dedicated contacts">
        <ul className="list-disc ml-6 space-y-1">
          <li>
            Privacy / GDPR requests —{" "}
            <A href="mailto:privacy@depscope.dev">privacy@depscope.dev</A>
          </li>
          <li>
            Security / vulnerability reports —{" "}
            <A href="mailto:security@depscope.dev">security@depscope.dev</A>
          </li>
          <li>
            Legal / IP complaints —{" "}
            <A href="mailto:legal@depscope.dev">legal@depscope.dev</A>
          </li>
          <li>
            Abuse / AUP violations —{" "}
            <A href="mailto:abuse@depscope.dev">abuse@depscope.dev</A>
          </li>
        </ul>
        <p className="mt-2 text-xs text-[var(--text-dim)]">All role-based addresses above forward to <A href="mailto:depscope@cuttalo.com">depscope@cuttalo.com</A>.</p>
      </Sec>

      <Sec id="odr" title="Online dispute resolution (EU consumers)">
        <p>
          Under Regulation (EU) 524/2013, EU consumers may access the European
          Commission&apos;s Online Dispute Resolution platform at{" "}
          <A href="https://ec.europa.eu/consumers/odr">
            ec.europa.eu/consumers/odr
          </A>
          . We also welcome direct contact at the addresses above.
        </p>
      </Sec>
    </LegalLayout>
  );
}
