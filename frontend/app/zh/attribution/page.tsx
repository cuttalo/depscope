import type { Metadata } from "next";
import { LegalLayoutZh, Sec, Strong, A } from "../../../components/legal/LegalLayoutZh";

export const metadata: Metadata = {
  title: "数据署名与许可 — DepScope",
  description: "DepScope 使用的公开数据源署名：OSV.dev、GitHub Advisory Database、软件包注册中心。",
  alternates: {
    canonical: "https://depscope.dev/zh/attribution",
    languages: {
      en: "https://depscope.dev/attribution",
      "zh-CN": "https://depscope.dev/zh/attribution",
    },
  },
};

export default function AttributionPage() {
  return (
    <LegalLayoutZh title="数据署名与许可" updated="2026年4月19日">
      <Sec id="intro" title="1. 概述">
        <p>
          DepScope 聚合并丰富下列来源的公开数据。本处的所有署名、链接和许可证适用于相应数据集，
          而非 DepScope 自身的软件或衍生分析。DepScope 自己的代码、UI、文档和专有健康评分
          © Cuttalo srl 版权所有。
        </p>
      </Sec>

      <Sec id="osv" title="2. OSV.dev（开源漏洞）">
        <p>
          漏洞记录来自 <A href="https://osv.dev">OSV.dev</A>，这是由 Google LLC 运营的开放分布式漏洞数据库。
          OSV.dev 聚合多个上游来源，每个来源都有自己的许可证（见下表）。
          DepScope 为每个漏洞展示返回原始 OSV 记录和上游来源的链接；我们应用过滤、去重、
          严重性推断和映射到内部 ID，但我们<Strong>不会</Strong>重新许可底层数据。
        </p>
        <div className="overflow-x-auto -mx-4 md:mx-0 mt-3">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-[var(--border)] text-left">
                <th className="py-2 pr-3">上游来源</th>
                <th className="py-2 pr-3">许可证</th>
                <th className="py-2 pr-3">DepScope 使用</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-[var(--border)] align-top"><td className="py-2 pr-3">GitHub Advisory Database (GHSA)</td><td className="py-2 pr-3">CC-BY-4.0</td><td className="py-2 pr-3">已摄取，按记录署名</td></tr>
              <tr className="border-b border-[var(--border)] align-top"><td className="py-2 pr-3">PyPI Advisory DB</td><td className="py-2 pr-3">CC-BY-4.0</td><td className="py-2 pr-3">已摄取，按记录署名</td></tr>
              <tr className="border-b border-[var(--border)] align-top"><td className="py-2 pr-3">Go Vulnerability DB</td><td className="py-2 pr-3">CC-BY-4.0</td><td className="py-2 pr-3">已摄取，按记录署名</td></tr>
              <tr className="border-b border-[var(--border)] align-top"><td className="py-2 pr-3">PSF Advisory DB</td><td className="py-2 pr-3">CC-BY-4.0</td><td className="py-2 pr-3">已摄取，按记录署名</td></tr>
              <tr className="border-b border-[var(--border)] align-top"><td className="py-2 pr-3">RustSec, GSD, Haskell, OCaml</td><td className="py-2 pr-3">CC0-1.0</td><td className="py-2 pr-3">已摄取（公共领域）</td></tr>
              <tr className="border-b border-[var(--border)] align-top"><td className="py-2 pr-3">OSS-Fuzz</td><td className="py-2 pr-3">CC-BY-4.0</td><td className="py-2 pr-3">已摄取，按记录署名</td></tr>
              <tr className="border-b border-[var(--border)] align-top"><td className="py-2 pr-3">RConsortium, Bitnami, OpenSSF Malicious Packages</td><td className="py-2 pr-3">Apache-2.0</td><td className="py-2 pr-3">已摄取，按记录署名</td></tr>
              <tr className="border-b border-[var(--border)] align-top"><td className="py-2 pr-3">Ubuntu Security Notices</td><td className="py-2 pr-3">CC-BY-SA-4.0</td><td className="py-2 pr-3"><Strong>被排除</Strong>（避免 share-alike）</td></tr>
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-xs">
          许可证分类基于 <A href="https://google.github.io/osv.dev">google.github.io/osv.dev</A> 上的 OSV.dev 上游文档。
        </p>
      </Sec>

      <Sec id="ghsa" title="3. GitHub Advisory Database">
        <p>
          部分漏洞数据来自 <A href="https://github.com/advisories">GitHub Advisory Database</A>（GHSA），
          许可为 <A href="https://creativecommons.org/licenses/by/4.0/">CC-BY-4.0</A>。
          个别咨询响应包含原始 GHSA 标识符和指向 github.com/advisories/GHSA-xxxx 的链接作为署名。
        </p>
      </Sec>

      <Sec id="registries" title="4. 软件包注册中心">
        <ul className="list-disc ml-6 space-y-1">
          <li><Strong>npm</Strong>：通过公开的 registry.npmjs.org API 实时获取元数据。</li>
          <li><Strong>PyPI</Strong>：PyPI® 是 Python Software Foundation (PSF) 的商标。</li>
          <li><Strong>crates.io</Strong>：由 Rust 基金会运营。</li>
          <li><Strong>Go proxy</Strong>：proxy.golang.org。</li>
          <li><Strong>Packagist (Composer)</Strong>、<Strong>Maven Central</Strong>（Sonatype）、<Strong>NuGet</Strong>、<Strong>RubyGems</Strong>、<Strong>pub.dev</Strong>、<Strong>hex.pm</Strong>、<Strong>Swift Package Index</Strong>、<Strong>CocoaPods</Strong>、<Strong>MetaCPAN</Strong>、<Strong>Hackage</Strong>、<Strong>CRAN</Strong>、<Strong>conda-forge</Strong>、<Strong>Homebrew</Strong>：各生态系统的公开 API/索引。</li>
        </ul>
        <p className="mt-2 text-xs">
          软件包元数据和徽标仍归其各自作者和社区所有。DepScope 将其呈现为实时查找和衍生分析，而非再分发数据集。
        </p>
      </Sec>

      <Sec id="trademarks" title="5. 商标">
        <p>
          Node.js®、Python®、Rust®、Ruby®、PHP®、Java®、.NET®、Go、Elixir、Swift、Dart、R、Haskell、
          npm、PyPI、Maven Central、Stripe®、Cloudflare®、Anthropic®、Claude® 等名称为其各自所有者的商标。
          提及并不暗示认可。
        </p>
      </Sec>

      <Sec id="derived" title="6. DepScope 生成的数据">
        <p>以下是 Cuttalo srl 的原创作品，受版权和数据库权法保护：</p>
        <ul className="list-disc ml-6 space-y-1 mt-2">
          <li><Strong>健康分算法</Strong>（权重、阈值、聚合指标）</li>
          <li><Strong>兼容性矩阵</Strong>（对/三元组兼容性推断）</li>
          <li><Strong>错误 → 修复</Strong> 知识库</li>
          <li>精选替代品和破坏性变更摘要</li>
          <li>服务源代码、UI、动画演示、文档</li>
        </ul>
        <p className="mt-2 text-xs">
          超出单个 API 查询范围重用 DepScope 生成的数据需要商业许可。
        </p>
      </Sec>

      <Sec id="takedown" title="7. 权利人联系方式">
        <p>
          如您是权利人并认为 DepScope 上的某些内容侵犯了您的权利，
          请发送邮件至 <A href="mailto:legal@depscope.dev">legal@depscope.dev</A>。
        </p>
      </Sec>
    </LegalLayoutZh>
  );
}
