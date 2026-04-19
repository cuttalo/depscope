import type { Metadata } from "next";
import { LegalLayoutZh, Sec, Strong, A } from "../../../components/legal/LegalLayoutZh";

export const metadata: Metadata = {
  title: "公司信息 — DepScope",
  description: "根据意大利 D.Lgs. 70/2003 第 7 条的 DepScope 法律披露。",
  alternates: {
    canonical: "https://depscope.dev/zh/imprint",
    languages: {
      en: "https://depscope.dev/imprint",
      "zh-CN": "https://depscope.dev/zh/imprint",
    },
  },
};

export default function ImprintPage() {
  return (
    <LegalLayoutZh title="公司信息" updated="2026年4月19日">
      <Sec id="company" title="公司">
        <p>
          <Strong>Cuttalo srl</Strong>
          <br />
          注册办事处：意大利
          <br />
          增值税号 / P.IVA：<Strong>IT03242390734</Strong>
          <br />
          一般联系：<A href="mailto:depscope@cuttalo.com">depscope@cuttalo.com</A>
        </p>
        <p className="mt-2 text-xs">
          根据 D.Lgs. 9 April 2003, n. 70（意大利电子商务法）第 7 条及意大利民法典第 2250 条提供本披露。
          完整注册详情（REA、PEC）可根据要求提供。
        </p>
      </Sec>

      <Sec id="representative" title="法定代表人">
        <p>公司法定代表人在意大利商业登记处注明。</p>
      </Sec>

      <Sec id="contacts" title="专用联系方式">
        <ul className="list-disc ml-6 space-y-1">
          <li>隐私 / GDPR 请求 — <A href="mailto:privacy@depscope.dev">privacy@depscope.dev</A></li>
          <li>安全 / 漏洞报告 — <A href="mailto:security@depscope.dev">security@depscope.dev</A></li>
          <li>法律 / 知识产权投诉 — <A href="mailto:legal@depscope.dev">legal@depscope.dev</A></li>
          <li>滥用 / AUP 违规 — <A href="mailto:abuse@depscope.dev">abuse@depscope.dev</A></li>
        </ul>
        <p className="mt-2 text-xs text-[var(--text-dim)]">上述所有角色邮箱地址均转发至 <A href="mailto:depscope@cuttalo.com">depscope@cuttalo.com</A>。</p>
      </Sec>

      <Sec id="odr" title="在线争议解决（欧盟消费者）">
        <p>
          根据欧盟第 524/2013 号条例，欧盟消费者可访问欧盟委员会的在线争议解决平台：
          <A href="https://ec.europa.eu/consumers/odr">ec.europa.eu/consumers/odr</A>。
        </p>
      </Sec>
    </LegalLayoutZh>
  );
}
