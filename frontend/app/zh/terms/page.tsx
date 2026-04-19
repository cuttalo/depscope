import type { Metadata } from "next";
import { LegalLayoutZh, Sec, Strong, A } from "../../../components/legal/LegalLayoutZh";

export const metadata: Metadata = {
  title: "服务条款 — DepScope",
  description: "您使用 DepScope API、仪表板和 MCP 服务器的条款。",
  alternates: {
    canonical: "https://depscope.dev/zh/terms",
    languages: {
      en: "https://depscope.dev/terms",
      "zh-CN": "https://depscope.dev/zh/terms",
    },
  },
};

export default function TermsPage() {
  return (
    <LegalLayoutZh title="服务条款" updated="2026年4月19日">
      <Sec id="acceptance" title="1. 接受">
        <p>
          本条款构成 <Strong>Cuttalo srl</Strong>（意大利，增值税号 IT03242390734，以下称 &ldquo;DepScope&rdquo;、&ldquo;我们&rdquo;）与您（以下称 &ldquo;客户&rdquo;、&ldquo;您&rdquo;）之间具有约束力的协议。访问 depscope.dev、其 API、仪表板、MCP 服务器或任何相关服务（以下称 &ldquo;服务&rdquo;）即表示您接受本条款、<A href="/zh/privacy">隐私政策</A>、<A href="/zh/aup">可接受使用政策</A> 和 <A href="/zh/cookies">Cookie 政策</A>。
        </p>
      </Sec>

      <Sec id="service" title="2. 服务">
        <p>
          DepScope 是一个软件包智能 API，从公共软件包注册中心（npm、PyPI、Cargo、Go 等 17 个生态系统）和安全源（OSV.dev、GitHub Advisory Database）聚合公开数据，帮助 AI 代理和开发者在安装前评估软件包。
        </p>
      </Sec>

      <Sec id="tiers" title="3. 层级、限制、计量">
        <ul className="list-disc ml-6 space-y-1">
          <li><Strong>免费层</Strong>：每个 IP 每分钟最多 200 个请求，无需身份验证，无正常运行承诺。</li>
          <li><Strong>付费层</Strong>（Pro、Team）：更高配额、API 密钥、优先支持。</li>
          <li>我们可全权决定更改配额、限流或临时暂停服务以保护系统完整性。</li>
          <li>单个客户在免费层的 <Strong>月度硬上限</Strong> 为 500 万请求；超出需升级付费层，否则可能被暂停。</li>
        </ul>
      </Sec>

      <Sec id="accounts" title="4. 账户和 API 密钥">
        <ul className="list-disc ml-6 space-y-1">
          <li>通过发送到您邮箱的魔术链接进行身份验证；不存储密码。</li>
          <li>您负责保密 API 密钥（<code>ds_live_*</code> 和 <code>ds_test_*</code>）。</li>
          <li>不得跨多个无关组织共享单个账户或密钥（不得转售免费层）。</li>
        </ul>
      </Sec>

      <Sec id="billing" title="5. 计费和退款（付费层）">
        <ul className="list-disc ml-6 space-y-1">
          <li>订阅按月或按年计费，以欧元（EUR）计价，通过 Stripe 支付。</li>
          <li><Strong>自动续订</Strong>：订阅自动续订直至取消。</li>
          <li><Strong>欧盟消费者</Strong>自购买起享有 14 天撤回权（D.Lgs. 21/2014）。</li>
          <li>我们可在下个计费周期前至少 30 天通知以修订价格。</li>
        </ul>
      </Sec>

      <Sec id="acceptable-use" title="6. 可接受使用">
        <p>您对服务的使用受我们的 <A href="/zh/aup">可接受使用政策</A> 约束。违规可能导致限流、暂停或终止，无需事先通知。</p>
      </Sec>

      <Sec id="data-disclaimers" title="7. 数据无保证">
        <p>
          DepScope 依赖第三方来源。漏洞数据、健康分数、弃用标记和版本信息可能不完整、延迟或不准确。
          <Strong>服务按 &ldquo;现状&rdquo; 和 &ldquo;可用&rdquo; 提供，在法律允许的最大范围内不提供任何明示、暗示、法定或其他保证</Strong>。
          您对基于 DepScope 输出做出的决策（包括在您的堆栈中安装哪些软件包）承担全部责任。
        </p>
      </Sec>

      <Sec id="ip" title="8. 知识产权">
        <p>
          DepScope 保留服务软件、设计、商标、文档和专有数据集（包括计算的健康分数）的所有权利。
          第三方数据（OSV.dev、GHSA、注册中心）仍归其各自所有者所有，受其许可证约束 — 见 <A href="/zh/attribution">/zh/attribution</A>。
        </p>
        <p className="mt-2">
          您不得：(i) 复制、修改或创建服务的衍生作品；(ii) 反编译、反汇编或逆向工程；
          (iii) 未经书面许可使用我们的名称、徽标或商标；(iv) 未经我们事先书面同意发布服务的比较基准。
        </p>
      </Sec>

      <Sec id="prohibited" title="9. 禁止行为">
        <ul className="list-disc ml-6 space-y-1">
          <li>违反任何适用法律或法规使用服务</li>
          <li>使用服务分发恶意软件、钓鱼或侵犯第三方知识产权的内容</li>
          <li>从受欧盟、联合国、美国 OFAC 或英国 HMT 制裁的司法管辖区访问服务</li>
          <li>向 API 提交个人数据、凭证或受监管数据</li>
          <li>未经授权访问、探测或破坏服务</li>
        </ul>
      </Sec>

      <Sec id="termination" title="10. 暂停和终止">
        <p>
          若您违反本条款、AUP 或适用法律，我们可在有或无通知的情况下暂停或终止您的访问权限。
          您可随时通过仪表板关闭账户或发送邮件至 <A href="mailto:depscope@cuttalo.com">depscope@cuttalo.com</A> 终止。
          终止后，您可在 30 天内导出账户数据。
        </p>
      </Sec>

      <Sec id="liability" title="11. 责任限制">
        <p>在意大利法律允许的最大范围内：</p>
        <ul className="list-disc ml-6 space-y-1 mt-2">
          <li>DepScope 对任何间接、附带、后果性、特殊或惩戒性损害（包括利润损失、数据丢失或业务中断）不承担责任。</li>
          <li>
            我们因服务引起或相关的任何索赔的总累计责任不超过 (a) <Strong>50 欧元</Strong>
            或 (b) 您在索赔发生前 <Strong>12 个月</Strong> 内向 DepScope 支付的费用中较高者。
          </li>
          <li>
            本条款不限制因重大过失、故意不当行为（<em>dolo</em>）、疏忽导致的死亡或人身伤害，
            或根据意大利民法典第 1229 条或适用消费者法不得排除的任何责任。
          </li>
        </ul>
      </Sec>

      <Sec id="indemnity" title="12. 赔偿">
        <p>
          您同意赔偿 Cuttalo srl 及其董事、员工和代理人因您违反本条款、滥用服务或违反任何法律或第三方权利而引起的任何第三方索赔。
        </p>
      </Sec>

      <Sec id="changes" title="13. 条款变更">
        <p>
          我们可能更新本条款。重大变更将通过邮件（注册用户）和站点横幅至少提前 <Strong>30 天</Strong> 宣布。
        </p>
      </Sec>

      <Sec id="misc" title="14. 其他">
        <ul className="list-disc ml-6 space-y-1">
          <li><Strong>可分割性</Strong>：若任何条款不可执行，其余条款继续有效。</li>
          <li><Strong>转让</Strong>：未经书面同意您不得转让；我们可向关联方或继任者转让。</li>
          <li><Strong>不弃权</Strong>：未执行某条款不视为放弃日后执行的权利。</li>
          <li><Strong>完整协议</Strong>：本条款连同链接文件构成双方之间的完整协议。</li>
          <li><Strong>不可抗力</Strong>：任何一方对超出合理控制范围事件导致的延迟或失败不承担责任。</li>
        </ul>
      </Sec>

      <Sec id="law" title="15. 适用法律和管辖权">
        <p>
          本条款受意大利法律管辖（不含冲突法规则和《联合国国际货物销售合同公约》）。
          争议的专属管辖权归属于 <Strong>意大利塔兰托法院</Strong>，消费者保护强制规定除外。
        </p>
      </Sec>

      <Sec id="contact" title="16. 联系">
        <p>
          Cuttalo srl — 意大利 — 增值税号 IT03242390734 —{" "}
          <A href="mailto:depscope@cuttalo.com">depscope@cuttalo.com</A>。
        </p>
      </Sec>
    </LegalLayoutZh>
  );
}
