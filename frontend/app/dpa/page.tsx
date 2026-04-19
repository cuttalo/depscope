import type { Metadata } from "next";
import { LegalLayout, Sec, Strong, A } from "../../components/legal/LegalLayout";

export const metadata: Metadata = {
  title: "Data Processing Addendum — DepScope",
  description:
    "DepScope Data Processing Addendum (DPA). GDPR art. 28 terms governing personal data processed on your behalf.",
  alternates: {
    canonical: "https://depscope.dev/dpa",
    languages: {
      en: "https://depscope.dev/dpa",
      "zh-CN": "https://depscope.dev/zh/dpa",
      "x-default": "https://depscope.dev/dpa",
    },
  },
};

export default function DPAPage() {
  return (
    <LegalLayout title="Data Processing Addendum" updated="April 19, 2026">
      <Sec id="intro" title="0. Overview and how to execute">
        <p>
          This Data Processing Addendum (&ldquo;<Strong>DPA</Strong>&rdquo;) forms part of
          the Terms of Service between <Strong>Cuttalo srl</Strong>, Italy
          (&ldquo;Processor&rdquo;) and the customer (&ldquo;Controller&rdquo;)
          using the paid tiers of DepScope. By subscribing to a Pro or Team
          plan and accepting our <A href="/terms">Terms</A>, the Controller is
          deemed to have entered into this DPA. A counter-signed PDF can be
          requested at{" "}
          <A href="mailto:privacy@depscope.dev">privacy@depscope.dev</A>.
        </p>
      </Sec>

      <Sec id="definitions" title="1. Definitions">
        <ul className="list-disc ml-6 space-y-1">
          <li>
            <Strong>GDPR</Strong>: Regulation (EU) 2016/679.
          </li>
          <li>
            <Strong>Personal Data</Strong>, <Strong>Processing</Strong>,{" "}
            <Strong>Data Subject</Strong>, <Strong>Controller</Strong>,{" "}
            <Strong>Processor</Strong>, <Strong>Sub-processor</Strong>: as
            defined in art. 4 GDPR.
          </li>
          <li>
            <Strong>Service</Strong>: the DepScope service made available by
            Cuttalo under the Terms of Service.
          </li>
          <li>
            <Strong>Customer Personal Data</Strong>: personal data processed
            by Cuttalo on the Controller&apos;s behalf in the course of
            providing the Service.
          </li>
        </ul>
      </Sec>

      <Sec id="roles" title="2. Roles and scope">
        <p>
          For Customer Personal Data processed through the Service, Cuttalo
          acts as Processor on behalf of the Controller. Each Party will
          comply with its obligations under GDPR and applicable data
          protection laws.
        </p>
      </Sec>

      <Sec id="subject-matter" title="3. Subject-matter, nature, purpose, duration">
        <ul className="list-disc ml-6 space-y-1">
          <li>
            <Strong>Subject-matter</Strong>: provision of the Service and
            related support.
          </li>
          <li>
            <Strong>Nature and purpose</Strong>: operating the API, storing
            account data, delivering authentication emails, metering usage,
            preventing abuse, billing.
          </li>
          <li>
            <Strong>Duration</Strong>: for the duration of the Agreement, plus
            retention periods stated in the{" "}
            <A href="/privacy#retention">Privacy Policy</A>.
          </li>
          <li>
            <Strong>Types of data</Strong>: email address, API key
            fingerprints, IP address (hashed), User-Agent, request metadata,
            billing identifiers.
          </li>
          <li>
            <Strong>Categories of Data Subjects</Strong>: the Controller&apos;s
            authorized users who access the Service.
          </li>
        </ul>
      </Sec>

      <Sec id="instructions" title="4. Processor obligations (art. 28(3) GDPR)">
        <p>
          Cuttalo shall:
        </p>
        <ul className="list-disc ml-6 space-y-1 mt-2">
          <li>
            Process Customer Personal Data only on documented instructions
            from the Controller (the Terms, this DPA, and the Controller&apos;s
            configuration of the Service constitute documented instructions);
          </li>
          <li>
            Ensure that persons authorized to process Customer Personal Data
            are subject to confidentiality obligations;
          </li>
          <li>
            Implement appropriate technical and organizational measures as
            described in <A href="/security">Annex II</A>;
          </li>
          <li>
            Assist the Controller in responding to Data Subject requests,
            breach notifications, and DPIAs (arts. 32-36 GDPR);
          </li>
          <li>
            Upon termination of the Service, delete or return all Customer
            Personal Data, unless law requires retention;
          </li>
          <li>
            Make available information necessary to demonstrate compliance
            and allow for audits as described in &sect; 8.
          </li>
        </ul>
      </Sec>

      <Sec id="sub-processors" title="5. Sub-processors (art. 28(2) GDPR)">
        <p>
          The Controller grants general authorization to Cuttalo to engage
          the sub-processors listed at{" "}
          <A href="/subprocessors">/subprocessors</A>. Cuttalo will give at
          least <Strong>30 days&apos; prior notice</Strong> before adding or
          replacing a sub-processor. The Controller may object on reasonable
          data-protection grounds; if no workable solution is found, the
          Controller may terminate the affected service.
        </p>
      </Sec>

      <Sec id="transfers" title="6. International transfers">
        <p>
          Where Customer Personal Data is transferred outside the EEA, the
          Parties agree that the transfer shall be subject to the{" "}
          <Strong>EU–US Data Privacy Framework</Strong> (where applicable)
          and/or the <Strong>Standard Contractual Clauses 2021/914</Strong>,
          Module 2 (Controller-to-Processor) or Module 3 (Processor-to-Sub-
          processor), which are hereby incorporated by reference. Annex I,
          II, and III to the SCCs are populated by reference to Annex I, II,
          III of this DPA.
        </p>
      </Sec>

      <Sec id="breach" title="7. Personal data breach">
        <p>
          Cuttalo will notify the Controller without undue delay after
          becoming aware of a Personal Data Breach affecting Customer
          Personal Data, and in any event within <Strong>48 hours</Strong>,
          providing the information reasonably available to enable the
          Controller to comply with art. 33 GDPR.
        </p>
      </Sec>

      <Sec id="audit" title="8. Audits and information rights">
        <p>
          The Controller may, on reasonable prior notice and no more than
          once per calendar year (unless a Personal Data Breach has occurred),
          request information necessary to demonstrate compliance. Cuttalo
          will make available audit reports, security documentation, and
          written responses. On-site audits may be arranged where strictly
          required by law, at the Controller&apos;s cost, under confidentiality.
        </p>
      </Sec>

      <Sec id="return" title="9. Return and deletion">
        <p>
          Within 30 days after termination of the Service, Cuttalo will
          delete or return, at the Controller&apos;s choice, all Customer
          Personal Data in its possession, subject to applicable legal
          retention obligations (e.g. art. 2220 Italian Civil Code for tax
          records).
        </p>
      </Sec>

      <Sec id="liability" title="10. Liability and precedence">
        <p>
          Liability under this DPA is subject to the limitations in the Terms
          of Service, save for liability that cannot be limited under art.
          1229 Italian Civil Code or GDPR art. 82. In case of conflict between
          this DPA and the Terms, this DPA prevails for matters relating to
          Processing of Customer Personal Data.
        </p>
      </Sec>

      <Sec id="law" title="11. Governing law">
        <p>
          Italian law; exclusive jurisdiction: Courts of Taranto, Italy, save
          for mandatory consumer-protection rules.
        </p>
      </Sec>

      <Sec id="annex-a" title="Annex I — Processing details">
        <ul className="list-disc ml-6 space-y-1">
          <li>
            <Strong>Data exporter</Strong>: the Controller (customer).
          </li>
          <li>
            <Strong>Data importer</Strong>: Cuttalo srl, Italy (Processor).
          </li>
          <li>
            <Strong>Nature / purpose</Strong>: provision of the DepScope
            Service.
          </li>
          <li>
            <Strong>Categories of Data Subjects</Strong>: Controller&apos;s
            authorized users.
          </li>
          <li>
            <Strong>Categories of personal data</Strong>: email, hashed IP,
            User-Agent, API key fingerprints, request metadata, billing
            identifiers.
          </li>
          <li>
            <Strong>Frequency</Strong>: continuous, for the duration of the
            Service.
          </li>
          <li>
            <Strong>Retention</Strong>: see <A href="/privacy#retention">Privacy &sect;5</A>.
          </li>
        </ul>
      </Sec>

      <Sec id="annex-b" title="Annex II — Technical and organizational measures">
        <p>
          See <A href="/security">/security</A> for the full description.
          Summary: TLS 1.2+, SHA-256 hashed API keys, no password storage,
          private network for DB, encrypted off-site backups on OVH
          Gravelines (EU), 6-hour automated alerts, 72-hour breach
          notification per GDPR.
        </p>
      </Sec>

      <Sec id="annex-c" title="Annex III — Authorized sub-processors">
        <p>
          See <A href="/subprocessors">/subprocessors</A> for the current
          list and change-notification procedure.
        </p>
      </Sec>
    </LegalLayout>
  );
}
