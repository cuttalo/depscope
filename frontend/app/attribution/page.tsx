import type { Metadata } from "next";
import { LegalLayout, Sec, Strong, A } from "../../components/legal/LegalLayout";

export const metadata: Metadata = {
  title: "Data Attribution & Licenses — DepScope",
  description:
    "Attribution for the public data sources used by DepScope: OSV.dev, GitHub Advisory Database, package registries.",
  alternates: {
    canonical: "https://depscope.dev/attribution",
    languages: {
      en: "https://depscope.dev/attribution",
      "zh-CN": "https://depscope.dev/zh/attribution",
      "x-default": "https://depscope.dev/attribution",
    },
  },
};

export default function AttributionPage() {
  return (
    <LegalLayout title="Data Attribution & Licenses" updated="April 19, 2026">
      <Sec id="intro" title="1. Overview">
        <p>
          DepScope aggregates and enriches public data from the sources below.
          All credits, links, and licenses stated here apply to the respective
          datasets, not to DepScope&apos;s own software or derived analytics.
          DepScope&apos;s own code, UI, documentation, and proprietary health
          scoring are © Cuttalo srl, all rights reserved unless an individual
          file states otherwise.
        </p>
      </Sec>

      <Sec id="osv" title="2. OSV.dev (Open Source Vulnerabilities)">
        <p>
          Vulnerability records are sourced from{" "}
          <A href="https://osv.dev">OSV.dev</A>, an open, distributed
          vulnerability database operated by Google LLC. Data is used under the
          terms published by OSV.dev and, where marked, the{" "}
          <A href="https://creativecommons.org/licenses/by/4.0/">
            Creative Commons Attribution 4.0 International (CC-BY-4.0)
          </A>{" "}
          license. Modifications made by DepScope include filtering,
          deduplication, severity inference, and mapping to our internal IDs.
          Source links in vulnerability responses point back to the original
          OSV records.
        </p>
      </Sec>

      <Sec id="ghsa" title="3. GitHub Advisory Database">
        <p>
          A portion of vulnerability data originates from the{" "}
          <A href="https://github.com/advisories">GitHub Advisory Database</A>{" "}
          (GHSA), licensed under{" "}
          <A href="https://creativecommons.org/licenses/by/4.0/">CC-BY-4.0</A>.
          Individual advisory responses include the original GHSA identifier
          and a link to github.com/advisories/GHSA-xxxx as attribution.
          Modifications: normalization into our schema, re-ranking by affected
          version presence in the latest release.
        </p>
      </Sec>

      <Sec id="registries" title="4. Package registries">
        <ul className="list-disc ml-6 space-y-1">
          <li>
            <Strong>npm</Strong> — metadata fetched live via the public{" "}
            <A href="https://registry.npmjs.org">registry.npmjs.org</A> API.
            npm, Inc. is a GitHub company. We do not redistribute npm data in
            bulk; responses are derived, cached, and served on demand.
          </li>
          <li>
            <Strong>PyPI</Strong> — via{" "}
            <A href="https://pypi.org/simple/">PyPI simple</A> and JSON API.
            PyPI® is a trademark of the Python Software Foundation (PSF).
          </li>
          <li>
            <Strong>crates.io</Strong> — operated by the Rust Foundation. Data
            via <A href="https://crates.io/api">crates.io public API</A>.
          </li>
          <li>
            <Strong>Go proxy</Strong> — <A href="https://proxy.golang.org">proxy.golang.org</A>.
          </li>
          <li>
            <Strong>Packagist (Composer)</Strong> —{" "}
            <A href="https://packagist.org">packagist.org</A>.
          </li>
          <li>
            <Strong>Maven Central</Strong> — via{" "}
            <A href="https://central.sonatype.org/">Sonatype</A>.
          </li>
          <li>
            <Strong>NuGet</Strong>, <Strong>RubyGems</Strong>,{" "}
            <Strong>pub.dev</Strong>, <Strong>hex.pm</Strong>,{" "}
            <Strong>Swift Package Index</Strong>, <Strong>CocoaPods</Strong>,{" "}
            <Strong>MetaCPAN</Strong>, <Strong>Hackage</Strong>,{" "}
            <Strong>CRAN</Strong>, <Strong>conda-forge</Strong>,{" "}
            <Strong>Homebrew</Strong> — public APIs/indexes of the respective
            ecosystems.
          </li>
        </ul>
        <p className="mt-2 text-xs">
          Package metadata and logos remain the property of their respective
          authors and communities. DepScope presents them as live lookups and
          derived analytics, not as a redistributed dataset.
        </p>
      </Sec>

      <Sec id="trademarks" title="5. Trademarks">
        <p>
          Node.js®, Python®, Rust®, Ruby®, PHP®, Java®, .NET®, Go, Elixir,
          Swift, Dart, R, Haskell, npm, PyPI, Maven Central, Stripe®,
          Cloudflare®, Anthropic®, Claude® and other names are trademarks of
          their respective owners. Mention does not imply endorsement.
        </p>
      </Sec>

      <Sec id="derived" title="6. DepScope-generated data">
        <p>
          The following are original works of Cuttalo srl and protected under
          copyright and database-right law:
        </p>
        <ul className="list-disc ml-6 space-y-1 mt-2">
          <li>
            <Strong>Health score algorithm</Strong> (weights, thresholds,
            aggregate metrics)
          </li>
          <li>
            <Strong>Compatibility Matrix</Strong> (pair/triple compatibility
            inferences)
          </li>
          <li>
            <Strong>Error&nbsp;→&nbsp;Fix</Strong> knowledge base
          </li>
          <li>Curated alternatives and breaking-change summaries</li>
          <li>
            The Service&apos;s source code, UI, animated pitch, documentation
          </li>
        </ul>
        <p className="mt-2 text-xs">
          Reuse of DepScope-generated data beyond individual API queries
          requires a commercial license.
        </p>
      </Sec>

      <Sec id="takedown" title="7. Rights-holder contact">
        <p>
          If you are a rights holder and believe something on DepScope
          infringes your rights, write to{" "}
          <A href="mailto:legal@depscope.dev">legal@depscope.dev</A> with (i)
          identification of the work, (ii) the URL at issue, (iii) your
          contact details, (iv) a statement of good-faith belief, and (v) a
          statement under penalty of perjury that you are authorized to act.
        </p>
      </Sec>
    </LegalLayout>
  );
}
