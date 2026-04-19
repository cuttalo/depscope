import type { Metadata } from "next";
import { LegalLayoutZh, Sec, Strong, A } from "../../../components/legal/LegalLayoutZh";

export const metadata: Metadata = {
  title: "数据处理附录 — DepScope",
  description:
    "DepScope 数据处理附录（DPA）。管理代表您处理个人数据的 GDPR 第 28 条条款。",
  alternates: {
    canonical: "https://depscope.dev/zh/dpa",
    languages: {
      en: "https://depscope.dev/dpa",
      "zh-CN": "https://depscope.dev/zh/dpa",
      "x-default": "https://depscope.dev/dpa",
    },
  },
};

export default function DPAPage() {
  return (
    <LegalLayoutZh title="数据处理附录" updated="2026年4月19日">
      <Sec id="intro" title="0. 概述和签署方式">
        <p>
          本数据处理附录（&ldquo;<Strong>DPA</Strong>&rdquo;）构成 <Strong>Cuttalo srl</Strong>（意大利，&ldquo;处理者&rdquo;）
          与使用 DepScope 付费层的客户（&ldquo;控制者&rdquo;）之间服务条款的一部分。
          通过订阅 Pro 或 Team 计划并接受我们的 <A href="/zh/terms">条款</A>，
          视为控制者已签署本 DPA。可向 <A href="mailto:depscope@cuttalo.com">depscope@cuttalo.com</A> 请求会签 PDF。
        </p>
      </Sec>

      <Sec id="definitions" title="1. 定义">
        <ul className="list-disc ml-6 space-y-1">
          <li><Strong>GDPR</Strong>：欧盟 2016/679 条例。</li>
          <li><Strong>个人数据</Strong>、<Strong>处理</Strong>、<Strong>数据主体</Strong>、<Strong>控制者</Strong>、<Strong>处理者</Strong>、<Strong>子处理者</Strong>：如 GDPR 第 4 条所定义。</li>
          <li><Strong>服务</Strong>：根据服务条款由 Cuttalo 提供的 DepScope 服务。</li>
          <li><Strong>客户个人数据</Strong>：Cuttalo 代表控制者在提供服务过程中处理的个人数据。</li>
        </ul>
      </Sec>

      <Sec id="roles" title="2. 角色和范围">
        <p>
          对于通过服务处理的客户个人数据，Cuttalo 作为代表控制者的处理者。
          每一方均应遵守 GDPR 和适用数据保护法下的义务。
        </p>
      </Sec>

      <Sec id="subject-matter" title="3. 主题、性质、目的、持续时间">
        <ul className="list-disc ml-6 space-y-1">
          <li><Strong>主题</Strong>：提供服务及相关支持。</li>
          <li><Strong>性质和目的</Strong>：运行 API、存储账户数据、发送身份验证邮件、计量使用、防止滥用、计费。</li>
          <li><Strong>持续时间</Strong>：协议期间，加上 <A href="/zh/privacy#retention">隐私政策</A> 中规定的保留期。</li>
          <li><Strong>数据类型</Strong>：邮箱、API 密钥指纹、IP 地址（哈希）、User-Agent、请求元数据、计费标识符。</li>
          <li><Strong>数据主体类别</Strong>：访问服务的控制者授权用户。</li>
        </ul>
      </Sec>

      <Sec id="instructions" title="4. 处理者义务（GDPR 第 28(3) 条）">
        <p>Cuttalo 应：</p>
        <ul className="list-disc ml-6 space-y-1 mt-2">
          <li>仅按控制者的书面指示处理客户个人数据；</li>
          <li>确保授权处理客户个人数据的人员负有保密义务；</li>
          <li>实施附录 II（<A href="/zh/security">/zh/security</A>）所述的适当技术和组织措施；</li>
          <li>协助控制者响应数据主体请求、违规通知和 DPIA（GDPR 第 32-36 条）；</li>
          <li>服务终止后，除非法律要求保留，否则删除或返还所有客户个人数据；</li>
          <li>提供证明合规性所需的信息并允许审计（见第 8 节）。</li>
        </ul>
      </Sec>

      <Sec id="sub-processors" title="5. 子处理者（GDPR 第 28(2) 条）">
        <p>
          控制者授予 Cuttalo 聘用 <A href="/zh/subprocessors">/zh/subprocessors</A> 所列子处理者的一般授权。
          Cuttalo 将在添加或替换子处理者前至少 <Strong>30 天</Strong> 通知。
        </p>
      </Sec>

      <Sec id="transfers" title="6. 国际传输">
        <p>
          当客户个人数据传输到 EEA 之外时，双方同意传输将受
          <Strong>欧盟-美国数据隐私框架</Strong>（适用时）和/或
          <Strong>标准合同条款 2021/914</Strong>（模块 2 或模块 3）约束。
        </p>
      </Sec>

      <Sec id="breach" title="7. 个人数据泄露">
        <p>
          Cuttalo 将在知悉影响客户个人数据的个人数据泄露后不迟延通知控制者，
          在任何情况下不迟于 <Strong>48 小时</Strong>。
        </p>
      </Sec>

      <Sec id="audit" title="8. 审计和信息权利">
        <p>
          控制者可在合理提前通知下每日历年一次（除非发生个人数据泄露）请求证明合规性所需的信息。
          Cuttalo 将提供审计报告、安全文档和书面回应。
        </p>
      </Sec>

      <Sec id="return" title="9. 返还和删除">
        <p>
          服务终止后 30 天内，Cuttalo 将按控制者选择删除或返还其持有的所有客户个人数据，
          受适用法律保留义务约束（例如意大利民法典第 2220 条规定的税务记录）。
        </p>
      </Sec>

      <Sec id="liability" title="10. 责任和优先顺序">
        <p>
          本 DPA 下的责任受服务条款中的限制约束，意大利民法典第 1229 条或 GDPR 第 82 条
          不能限制的责任除外。本 DPA 与条款冲突时，关于客户个人数据处理事项以本 DPA 为准。
        </p>
      </Sec>

      <Sec id="law" title="11. 适用法律">
        <p>意大利法律；专属管辖权：意大利塔兰托法院，消费者保护强制规定除外。</p>
      </Sec>

      <Sec id="annex-a" title="附录 I — 处理详情">
        <ul className="list-disc ml-6 space-y-1">
          <li><Strong>数据输出方</Strong>：控制者（客户）。</li>
          <li><Strong>数据输入方</Strong>：Cuttalo srl，意大利（处理者）。</li>
          <li><Strong>性质 / 目的</Strong>：提供 DepScope 服务。</li>
          <li><Strong>数据主体类别</Strong>：控制者的授权用户。</li>
          <li><Strong>个人数据类别</Strong>：邮箱、哈希 IP、User-Agent、API 密钥指纹、请求元数据、计费标识符。</li>
          <li><Strong>频率</Strong>：连续，服务期间。</li>
          <li><Strong>保留</Strong>：见 <A href="/zh/privacy#retention">隐私 &sect;4</A>。</li>
        </ul>
      </Sec>

      <Sec id="annex-b" title="附录 II — 技术和组织措施">
        <p>
          完整描述见 <A href="/zh/security">/zh/security</A>。
          摘要：TLS 1.2+、SHA-256 哈希的 API 密钥、不存储密码、数据库私有网络、
          OVH Gravelines（欧盟）的加密异地备份、每 6 小时自动警报、GDPR 规定的 72 小时违规通知。
        </p>
      </Sec>

      <Sec id="annex-c" title="附录 III — 授权的子处理者">
        <p>
          当前列表和变更通知程序见 <A href="/zh/subprocessors">/zh/subprocessors</A>。
        </p>
      </Sec>
    </LegalLayoutZh>
  );
}
