"""Mass populate DepScope with under-represented ecosystems.

Targets:
  maven     1500   (from 243)
  go         500   (from  95)
  swift      200   (from  23)
  pub        300   (from 102)
  hex        300   (from  99)
  homebrew   300   (from 131)
  hackage    300   (from 113)
  cpan       300   (from 102)
  cran       300   (from 124)
  conda      300   (from 116)
  cocoapods  300   (from 102)

Uses existing fetchers in api/registries.py — no modifications to them.
Rate limits: 1s between calls to SAME registry, 0.3s between packages overall.
Idempotent: ON CONFLICT DO UPDATE (already in save_package_to_db).
"""
import asyncio
import aiohttp
import sys
import time
import logging
import os

sys.path.insert(0, "/home/deploy/depscope")

from api.registries import fetch_package, fetch_vulnerabilities, save_package_to_db
from api.health import calculate_health_score
from api.cache import cache_set
from api.database import get_pool


LOG_FILE = "/var/log/depscope/mass_populate.log"
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("mass_populate")


# ═══════════════════════════════════════════════════════════════
# TARGETS
# ═══════════════════════════════════════════════════════════════
TARGETS = {
    "maven": 1500,
    "go": 500,
    "swift": 200,
    "pub": 300,
    "hex": 300,
    "homebrew": 300,
    "hackage": 300,
    "cpan": 300,
    "cran": 300,
    "conda": 300,
    "cocoapods": 300,
}

# Overall time budget: 4h
MAX_RUN_SECONDS = 4 * 60 * 60
# Per-registry time budget (30min) to skip slow ones
MAX_REGISTRY_SECONDS = 30 * 60

HTTP_TIMEOUT = aiohttp.ClientTimeout(total=15)
HEADERS = {"User-Agent": "DepScope/1.0 (+https://depscope.dev)"}


# ═══════════════════════════════════════════════════════════════
# LIST BUILDERS — per ecosystem
# ═══════════════════════════════════════════════════════════════

async def list_maven(session) -> list[str]:
    """Maven Central Solr. Fetch multiple popular groups + generic top."""
    names: list[str] = []
    seen: set[str] = set()
    groups = [
        "org.springframework", "org.springframework.boot", "org.springframework.cloud",
        "org.springframework.data", "org.springframework.security",
        "org.apache.commons", "org.apache.maven", "org.apache.maven.plugins",
        "org.apache.logging.log4j", "org.apache.httpcomponents",
        "org.apache.kafka", "org.apache.hadoop", "org.apache.spark", "org.apache.flink",
        "org.apache.tomcat", "org.apache.poi", "org.apache.lucene",
        "io.spring.gradle", "io.projectreactor", "io.netty", "io.grpc",
        "io.micrometer", "io.jsonwebtoken", "io.swagger", "io.swagger.core.v3",
        "io.vertx", "io.micronaut", "io.quarkus", "io.dropwizard",
        "com.google.guava", "com.google.code.gson", "com.google.protobuf",
        "com.google.firebase", "com.google.cloud", "com.google.android",
        "com.fasterxml.jackson.core", "com.fasterxml.jackson.databind",
        "com.fasterxml.jackson.module", "com.fasterxml.jackson.dataformat",
        "com.squareup.okhttp3", "com.squareup.retrofit2", "com.squareup.moshi",
        "com.squareup", "com.squareup.okio",
        "junit", "org.junit.jupiter", "org.junit.platform",
        "org.mockito", "org.hamcrest", "org.assertj",
        "org.slf4j", "ch.qos.logback", "org.apache.logging",
        "org.postgresql", "mysql", "com.h2database", "org.hsqldb",
        "org.hibernate", "org.hibernate.orm", "org.hibernate.validator",
        "com.zaxxer", "org.apache.commons", "commons-io", "commons-lang",
        "commons-codec", "commons-collections", "commons-logging",
        "org.eclipse.jetty", "org.glassfish.jersey.core", "org.glassfish",
        "org.jetbrains.kotlin", "org.jetbrains.kotlinx", "org.jetbrains",
        "org.scala-lang", "com.typesafe", "com.typesafe.akka",
        "org.clojure", "org.elasticsearch", "org.elasticsearch.client",
        "redis.clients", "io.lettuce", "org.mongodb",
        "com.amazonaws", "software.amazon.awssdk",
        "io.opentelemetry", "io.prometheus", "io.sentry",
        "org.yaml", "com.thoughtworks.xstream",
        "org.projectlombok", "org.mapstruct",
        "com.github.javaparser", "org.ow2.asm",
        "com.auth0", "com.nimbusds",
        "org.keycloak", "org.bouncycastle",
        "org.testcontainers", "io.cucumber", "org.seleniumhq.selenium",
        "com.google.errorprone", "com.google.code.findbugs",
        "org.apache.camel", "org.apache.activemq", "org.apache.zookeeper",
        "org.apache.curator", "org.apache.thrift",
        "org.quartz-scheduler", "org.xerial", "org.xerial.snappy",
        "io.reactivex.rxjava3", "io.reactivex.rxjava2", "io.reactivex",
        "com.lmax", "net.java.dev.jna",
    ]
    for g in groups:
        if len(names) >= 2000:
            break
        url = f"https://search.maven.org/solrsearch/select?q=g:{g}&rows=200&wt=json"
        try:
            async with session.get(url, timeout=HTTP_TIMEOUT, headers=HEADERS) as r:
                if r.status != 200:
                    continue
                data = await r.json(content_type=None)
                for doc in data.get("response", {}).get("docs", []):
                    a = doc.get("a")
                    gg = doc.get("g")
                    if a and gg:
                        name = f"{gg}:{a}"
                        if name not in seen:
                            seen.add(name)
                            names.append(name)
        except Exception as e:
            log.warning(f"maven group {g}: {e}")
        await asyncio.sleep(0.5)
    log.info(f"[maven] collected {len(names)} candidates")
    return names


# Curated Go module list — extended
GO_MODULES = [
    # web frameworks
    "github.com/gin-gonic/gin", "github.com/labstack/echo/v4", "github.com/gofiber/fiber/v2",
    "github.com/go-chi/chi/v5", "github.com/gorilla/mux", "github.com/gorilla/websocket",
    "github.com/gorilla/sessions", "github.com/gorilla/handlers", "github.com/gorilla/schema",
    "github.com/beego/beego/v2", "github.com/revel/revel", "github.com/kataras/iris/v12",
    "github.com/valyala/fasthttp", "github.com/emicklei/go-restful/v3",
    # logging
    "github.com/sirupsen/logrus", "go.uber.org/zap", "github.com/rs/zerolog",
    "github.com/op/go-logging", "github.com/golang/glog", "golang.org/x/exp/slog",
    # config/cli
    "github.com/spf13/cobra", "github.com/spf13/viper", "github.com/spf13/pflag",
    "github.com/spf13/afero", "github.com/urfave/cli/v2", "github.com/alecthomas/kong",
    "github.com/jessevdk/go-flags", "github.com/mitchellh/cli",
    # testing
    "github.com/stretchr/testify", "github.com/onsi/ginkgo/v2", "github.com/onsi/gomega",
    "github.com/golang/mock", "go.uber.org/mock", "github.com/DATA-DOG/go-sqlmock",
    "github.com/jarcoal/httpmock", "github.com/h2non/gock",
    # db
    "gorm.io/gorm", "gorm.io/driver/postgres", "gorm.io/driver/mysql", "gorm.io/driver/sqlite",
    "github.com/jmoiron/sqlx", "github.com/jackc/pgx/v5", "github.com/lib/pq",
    "github.com/go-sql-driver/mysql", "github.com/mattn/go-sqlite3",
    "github.com/uptrace/bun", "entgo.io/ent", "github.com/volatiletech/sqlboiler/v4",
    "github.com/georgysavva/scany/v2",
    # cache
    "github.com/redis/go-redis/v9", "github.com/go-redis/redis/v8", "github.com/gomodule/redigo",
    "github.com/bradfitz/gomemcache", "github.com/allegro/bigcache/v3",
    "github.com/patrickmn/go-cache", "github.com/coocood/freecache",
    "github.com/dgraph-io/ristretto", "github.com/hashicorp/golang-lru/v2",
    # messaging
    "github.com/nats-io/nats.go", "github.com/rabbitmq/amqp091-go", "github.com/streadway/amqp",
    "github.com/segmentio/kafka-go", "github.com/IBM/sarama", "github.com/Shopify/sarama",
    "github.com/confluentinc/confluent-kafka-go/v2", "github.com/eclipse/paho.mqtt.golang",
    "github.com/ThreeDotsLabs/watermill", "github.com/nsqio/go-nsq",
    # auth / jwt / crypto
    "github.com/golang-jwt/jwt/v5", "github.com/dgrijalva/jwt-go", "github.com/lestrrat-go/jwx/v2",
    "github.com/coreos/go-oidc/v3", "golang.org/x/oauth2", "github.com/markbates/goth",
    "github.com/google/uuid", "github.com/gofrs/uuid/v5", "github.com/rs/xid",
    "github.com/segmentio/ksuid", "github.com/oklog/ulid/v2",
    "golang.org/x/crypto", "github.com/golang-jwt/jwt",
    # http / clients
    "github.com/go-resty/resty/v2", "github.com/hashicorp/go-retryablehttp",
    "github.com/imroc/req/v3", "github.com/parnurzeal/gorequest",
    "github.com/carlmjohnson/requests",
    # validation
    "github.com/go-playground/validator/v10", "github.com/asaskevich/govalidator",
    "github.com/go-ozzo/ozzo-validation/v4",
    # serialization / parsing
    "github.com/tidwall/gjson", "github.com/tidwall/sjson", "github.com/tidwall/buntdb",
    "github.com/json-iterator/go", "github.com/goccy/go-json", "github.com/bytedance/sonic",
    "gopkg.in/yaml.v3", "gopkg.in/yaml.v2", "github.com/pelletier/go-toml/v2",
    "github.com/BurntSushi/toml", "github.com/mitchellh/mapstructure",
    "github.com/hashicorp/hcl/v2",
    # tui / color
    "github.com/fatih/color", "github.com/charmbracelet/bubbletea",
    "github.com/charmbracelet/lipgloss", "github.com/charmbracelet/bubbles",
    "github.com/charmbracelet/log", "github.com/charmbracelet/glamour",
    "github.com/mattn/go-runewidth", "github.com/mattn/go-isatty",
    "github.com/mattn/go-colorable", "github.com/briandowns/spinner",
    "github.com/schollz/progressbar/v3", "github.com/cheggaaa/pb/v3",
    "github.com/manifoldco/promptui", "github.com/AlecAivazis/survey/v2",
    # observability
    "github.com/prometheus/client_golang", "github.com/prometheus/common",
    "github.com/prometheus/client_model", "github.com/prometheus/procfs",
    "go.opentelemetry.io/otel", "go.opentelemetry.io/otel/trace",
    "go.opentelemetry.io/otel/sdk", "go.opentelemetry.io/otel/exporters/otlp/otlptrace",
    "github.com/open-telemetry/opentelemetry-go",
    "github.com/getsentry/sentry-go", "github.com/uber/jaeger-client-go",
    "github.com/newrelic/go-agent/v3",
    # rpc / grpc
    "google.golang.org/grpc", "google.golang.org/protobuf", "google.golang.org/genproto",
    "github.com/grpc-ecosystem/grpc-gateway/v2", "github.com/grpc-ecosystem/go-grpc-middleware",
    "connectrpc.com/connect", "github.com/twitchtv/twirp",
    # cloud sdks
    "github.com/aws/aws-sdk-go-v2", "github.com/aws/aws-sdk-go-v2/config",
    "github.com/aws/aws-sdk-go-v2/credentials", "github.com/aws/aws-sdk-go-v2/service/s3",
    "github.com/aws/aws-sdk-go-v2/service/dynamodb", "github.com/aws/aws-sdk-go-v2/service/sqs",
    "github.com/aws/aws-sdk-go-v2/service/sns", "github.com/aws/aws-sdk-go-v2/service/lambda",
    "github.com/aws/aws-sdk-go", "github.com/aws/aws-lambda-go",
    "cloud.google.com/go", "cloud.google.com/go/storage", "cloud.google.com/go/pubsub",
    "cloud.google.com/go/firestore", "cloud.google.com/go/bigquery",
    "github.com/Azure/azure-sdk-for-go", "github.com/Azure/azure-sdk-for-go/sdk/azcore",
    "github.com/Azure/go-autorest/autorest", "github.com/Azure/azure-storage-blob-go",
    # k8s / infra
    "k8s.io/client-go", "k8s.io/api", "k8s.io/apimachinery", "k8s.io/apiextensions-apiserver",
    "k8s.io/kubectl", "sigs.k8s.io/controller-runtime", "sigs.k8s.io/yaml",
    "github.com/kubernetes-sigs/kustomize", "helm.sh/helm/v3",
    "github.com/hashicorp/terraform-plugin-sdk/v2",
    "github.com/hashicorp/consul/api", "github.com/hashicorp/vault/api",
    "github.com/hashicorp/go-version", "github.com/hashicorp/go-multierror",
    "github.com/hashicorp/golang-lru", "github.com/hashicorp/hcl",
    "github.com/hashicorp/go-plugin", "github.com/hashicorp/raft",
    # docker / container
    "github.com/docker/docker", "github.com/docker/cli", "github.com/docker/go-connections",
    "github.com/docker/go-units", "github.com/containerd/containerd", "github.com/opencontainers/runc",
    "github.com/opencontainers/image-spec",
    # x/tools / net / sys
    "golang.org/x/net", "golang.org/x/text", "golang.org/x/sync",
    "golang.org/x/sys", "golang.org/x/tools", "golang.org/x/time",
    "golang.org/x/mod", "golang.org/x/exp", "golang.org/x/term",
    "golang.org/x/image", "golang.org/x/xerrors", "golang.org/x/sync/errgroup",
    # migrations / schedulers
    "github.com/golang-migrate/migrate/v4", "github.com/pressly/goose/v3",
    "github.com/robfig/cron/v3", "github.com/go-co-op/gocron/v2",
    # graph / orm helpers
    "entgo.io/contrib", "github.com/graphql-go/graphql", "github.com/99designs/gqlgen",
    "github.com/vektah/gqlparser/v2",
    # ai / ml
    "github.com/sashabaranov/go-openai", "github.com/tmc/langchaingo",
    "github.com/yuin/goldmark", "github.com/russross/blackfriday/v2",
    # templates / rendering
    "github.com/flosch/pongo2/v6", "github.com/a-h/templ", "github.com/Masterminds/sprig/v3",
    # system / IO
    "github.com/fsnotify/fsnotify", "github.com/klauspost/compress",
    "github.com/ulikunitz/xz", "github.com/dsnet/compress",
    "github.com/shirou/gopsutil/v3", "github.com/pkg/errors", "github.com/pkg/sftp",
    # crypto coins / finance
    "github.com/ethereum/go-ethereum", "github.com/btcsuite/btcd",
    # feature flags
    "github.com/open-feature/go-sdk", "gopkg.in/DataDog/dd-trace-go.v1",
    # other pop
    "github.com/patrickmn/go-cache", "github.com/panjf2000/ants/v2",
    "github.com/gofrs/flock", "github.com/cenkalti/backoff/v4",
    "github.com/avast/retry-go/v4", "github.com/eapache/go-resiliency",
    "github.com/dgraph-io/badger/v4", "github.com/etcd-io/bbolt",
    "go.etcd.io/bbolt", "go.etcd.io/etcd/client/v3",
    "github.com/go-git/go-git/v5", "github.com/google/go-github/v62",
    "github.com/google/go-cmp", "github.com/google/go-containerregistry",
    "github.com/google/wire", "github.com/google/gopacket",
    "github.com/minio/minio-go/v7", "github.com/spiffe/go-spiffe/v2",
    "github.com/slack-go/slack", "github.com/bwmarrin/discordgo",
    "github.com/go-telegram-bot-api/telegram-bot-api/v5",
    "github.com/gocolly/colly/v2", "github.com/PuerkitoBio/goquery",
    "github.com/chromedp/chromedp", "github.com/playwright-community/playwright-go",
    "github.com/elastic/go-elasticsearch/v8", "github.com/olivere/elastic/v7",
    "github.com/jinzhu/copier", "github.com/jinzhu/now",
    "github.com/xanzy/go-gitlab", "github.com/ktr0731/go-fuzzyfinder",
    "github.com/samber/lo", "github.com/samber/do/v2", "github.com/samber/mo",
    "github.com/life4/genesis", "github.com/ahmetb/go-linq/v3",
    "github.com/go-oauth2/oauth2/v4", "github.com/casbin/casbin/v2",
    "github.com/volatiletech/authboss/v3", "github.com/unrolled/secure",
    "github.com/gin-contrib/cors", "github.com/gin-contrib/sessions",
    "github.com/gin-contrib/zap", "github.com/rs/cors",
    "github.com/justinas/alice", "github.com/felixge/httpsnoop",
    "github.com/didip/tollbooth/v7", "golang.org/x/time/rate",
    "github.com/aws/smithy-go", "github.com/oracle/oci-go-sdk/v65",
    "github.com/digitalocean/godo", "github.com/linode/linodego",
    "github.com/scaleway/scaleway-sdk-go", "github.com/ovh/go-ovh",
    "github.com/cloudflare/cloudflare-go", "github.com/cloudflare/circl",
    "github.com/gliderlabs/ssh", "golang.org/x/term",
    "github.com/creack/pty", "github.com/containerd/console",
    "github.com/nxadm/tail", "github.com/hpcloud/tail",
    "github.com/prometheus/alertmanager", "github.com/grafana/loki",
    "github.com/grafana/grafana-plugin-sdk-go",
    "github.com/influxdata/influxdb-client-go/v2", "github.com/influxdata/telegraf",
    "github.com/nats-io/jetstream", "github.com/nats-io/nkeys",
    "github.com/ClickHouse/clickhouse-go/v2", "github.com/go-mysql-org/go-mysql",
    "go.mongodb.org/mongo-driver", "github.com/arangodb/go-driver",
    "github.com/neo4j/neo4j-go-driver/v5", "github.com/olivere/vfs",
    "github.com/apache/arrow/go/v15", "github.com/apache/pulsar-client-go",
    "github.com/ipfs/go-ipfs-api", "github.com/libp2p/go-libp2p",
    "github.com/multiformats/go-multihash", "github.com/multiformats/go-multiaddr",
    "github.com/planetscale/vtprotobuf", "buf.build/gen/go/bufbuild/protoschema/protocolbuffers/go",
    "github.com/mattn/go-sqlite3", "modernc.org/sqlite",
    "github.com/urfave/negroni/v3", "github.com/felixge/fgprof",
    "github.com/pkg/profile", "github.com/google/pprof",
    "github.com/dominikbraun/graph", "github.com/heimdalr/dag",
    "github.com/xuri/excelize/v2", "github.com/tealeg/xlsx/v3",
    "github.com/unidoc/unipdf/v3", "github.com/signintech/gopdf",
    "github.com/ledongthuc/pdf", "github.com/jung-kurt/gofpdf",
    "github.com/disintegration/imaging", "github.com/nfnt/resize",
    "github.com/chai2010/webp", "github.com/h2non/bimg",
    "github.com/dhowden/tag", "github.com/asticode/go-astisub",
    "github.com/u-root/u-root", "github.com/u-root/uio",
    "github.com/coreos/go-systemd/v22", "github.com/cilium/ebpf",
    "github.com/google/nftables", "github.com/mdlayher/netlink",
    "github.com/miekg/dns", "github.com/pion/webrtc/v4",
    "github.com/pion/rtp", "github.com/pion/rtcp",
    "github.com/quic-go/quic-go", "github.com/lucas-clemente/quic-go",
    "github.com/gorilla/csrf", "github.com/unrolled/render",
    "github.com/unrolled/logger", "github.com/felixge/httpsnoop",
    "github.com/Azure/go-amqp", "github.com/jmespath/go-jmespath",
    "github.com/99designs/keyring", "github.com/zalando/go-keyring",
    "github.com/keybase/go-keychain", "github.com/awnumar/memguard",
    "github.com/robotn/gohook", "github.com/go-vgo/robotgo",
    "github.com/go-gl/glfw/v3.3/glfw", "github.com/hajimehoshi/ebiten/v2",
    "fyne.io/fyne/v2", "github.com/andlabs/ui",
    "github.com/webview/webview", "github.com/wailsapp/wails/v2",
    "github.com/zserge/lorca", "github.com/sciter-sdk/go-sciter",
    "github.com/labstack/gommon", "github.com/dchest/uniuri",
    "github.com/ajg/form", "github.com/gorilla/feeds",
    "github.com/mmcdole/gofeed", "github.com/SlyMarbo/rss",
    "github.com/spf13/jwalterweatherman", "github.com/spf13/nitro",
    "github.com/ziutek/mymysql", "github.com/denisenkom/go-mssqldb",
    "github.com/sijms/go-ora/v2", "github.com/godror/godror",
    "github.com/rqlite/rqlite", "github.com/dgraph-io/dgraph",
    "github.com/coreos/etcd", "github.com/tikv/client-go/v2",
    "github.com/cockroachdb/pebble", "github.com/linxGnu/grocksdb",
    "github.com/twpayne/go-geom", "github.com/paulmach/orb",
    "github.com/peterstace/simplefeatures", "github.com/golang/geo",
    "github.com/google/s2-geometry-library-go", "github.com/kellydunn/golang-geo",
    "github.com/umahmood/haversine", "github.com/mmcloughlin/geohash",
    "github.com/fogleman/gg", "github.com/llgcode/draw2d",
    "github.com/lucasb-eyer/go-colorful", "github.com/fatih/structs",
    "github.com/jedib0t/go-pretty/v6", "github.com/olekukonko/tablewriter",
    "github.com/apcera/termtables", "github.com/gosuri/uitable",
    "github.com/hokaccha/go-prettyjson", "github.com/tidwall/pretty",
    "github.com/nicksnyder/go-i18n/v2", "golang.org/x/text/language",
    "github.com/robert-nix/ansihtml", "github.com/tmc/grpc-websocket-proxy",
    "github.com/go-openapi/runtime", "github.com/go-openapi/strfmt",
    "github.com/go-openapi/swag", "github.com/go-openapi/validate",
    "github.com/swaggo/swag", "github.com/swaggo/gin-swagger",
    "github.com/deepmap/oapi-codegen/v2", "github.com/getkin/kin-openapi",
]

async def list_go(session) -> list[str]:
    # Curated list is enough; proxy.golang.org has no search.
    log.info(f"[go] curated list size {len(GO_MODULES)}")
    return GO_MODULES[:]


async def list_swift(session) -> list[str]:
    """Swift Package Index has a packages list."""
    names: list[str] = []
    urls = [
        "https://swiftpackageindex.com/packages.json",
        "https://swiftpackageindex.com/api/packages.json",
    ]
    for url in urls:
        try:
            async with session.get(url, timeout=HTTP_TIMEOUT, headers=HEADERS) as r:
                if r.status != 200:
                    continue
                data = await r.json(content_type=None)
                items = data if isinstance(data, list) else data.get("packages", data.get("data", []))
                for it in items:
                    if isinstance(it, str):
                        names.append(it)
                    elif isinstance(it, dict):
                        url_ = it.get("packageUrl") or it.get("url") or it.get("repositoryUrl")
                        if url_:
                            names.append(url_)
                if names:
                    break
        except Exception as e:
            log.warning(f"swift list {url}: {e}")
    # Fallback curated list
    if len(names) < 200:
        curated = [
            "https://github.com/Alamofire/Alamofire",
            "https://github.com/ReactiveX/RxSwift",
            "https://github.com/SnapKit/SnapKit",
            "https://github.com/onevcat/Kingfisher",
            "https://github.com/SwiftyJSON/SwiftyJSON",
            "https://github.com/vapor/vapor",
            "https://github.com/vapor/fluent",
            "https://github.com/vapor/fluent-postgres-driver",
            "https://github.com/apple/swift-nio",
            "https://github.com/apple/swift-log",
            "https://github.com/apple/swift-metrics",
            "https://github.com/apple/swift-crypto",
            "https://github.com/apple/swift-collections",
            "https://github.com/apple/swift-algorithms",
            "https://github.com/apple/swift-argument-parser",
            "https://github.com/apple/swift-syntax",
            "https://github.com/apple/swift-async-algorithms",
            "https://github.com/apple/swift-atomics",
            "https://github.com/apple/swift-format",
            "https://github.com/apple/swift-protobuf",
            "https://github.com/apple/swift-package-manager",
            "https://github.com/apple/swift-system",
            "https://github.com/apple/swift-http-types",
            "https://github.com/apple/swift-openapi-generator",
            "https://github.com/apple/swift-openapi-runtime",
            "https://github.com/apple/swift-certificates",
            "https://github.com/apple/swift-distributed-tracing",
            "https://github.com/apple/swift-service-lifecycle",
            "https://github.com/apple/swift-markdown",
            "https://github.com/apple/swift-numerics",
            "https://github.com/pointfreeco/swift-composable-architecture",
            "https://github.com/pointfreeco/swift-dependencies",
            "https://github.com/pointfreeco/swift-snapshot-testing",
            "https://github.com/pointfreeco/swift-case-paths",
            "https://github.com/pointfreeco/swift-custom-dump",
            "https://github.com/pointfreeco/swift-identified-collections",
            "https://github.com/pointfreeco/swift-parsing",
            "https://github.com/pointfreeco/swift-tagged",
            "https://github.com/pointfreeco/swift-url-routing",
            "https://github.com/pointfreeco/swift-navigation",
            "https://github.com/pointfreeco/swift-concurrency-extras",
            "https://github.com/pointfreeco/swift-perception",
            "https://github.com/pointfreeco/swift-sharing",
            "https://github.com/airbnb/lottie-ios",
            "https://github.com/realm/realm-swift",
            "https://github.com/stephencelis/SQLite.swift",
            "https://github.com/groue/GRDB.swift",
            "https://github.com/firebase/firebase-ios-sdk",
            "https://github.com/getsentry/sentry-cocoa",
            "https://github.com/stripe/stripe-ios",
            "https://github.com/auth0/Auth0.swift",
            "https://github.com/auth0/JWTDecode.swift",
            "https://github.com/kishikawakatsumi/KeychainAccess",
            "https://github.com/scinfu/SwiftSoup",
            "https://github.com/ReactiveCocoa/ReactiveSwift",
            "https://github.com/ReactiveCocoa/ReactiveCocoa",
            "https://github.com/mxcl/PromiseKit",
            "https://github.com/Moya/Moya",
            "https://github.com/realm/SwiftLint",
            "https://github.com/nicklockwood/SwiftFormat",
            "https://github.com/yonaskolb/XcodeGen",
            "https://github.com/tuist/tuist",
            "https://github.com/CocoaLumberjack/CocoaLumberjack",
            "https://github.com/MessageKit/MessageKit",
            "https://github.com/hyperoslo/Cache",
            "https://github.com/JohnEstropia/CoreStore",
            "https://github.com/ReSwift/ReSwift",
            "https://github.com/kean/Nuke",
            "https://github.com/daltoniam/Starscream",
            "https://github.com/exyte/ConcentricOnboarding",
            "https://github.com/exyte/PopupView",
            "https://github.com/exyte/ActivityIndicatorView",
            "https://github.com/exyte/Chat",
            "https://github.com/siteline/SwiftUI-Introspect",
            "https://github.com/hmlongco/Factory",
            "https://github.com/hmlongco/Resolver",
            "https://github.com/groue/Schedulers",
            "https://github.com/CombineCommunity/CombineExt",
            "https://github.com/CombineCommunity/RxCombine",
            "https://github.com/krzyzanowskim/CryptoSwift",
            "https://github.com/httpswift/swifter",
            "https://github.com/tid-kijyun/Kanna",
            "https://github.com/malcommac/SwiftDate",
            "https://github.com/malcommac/SwiftRichString",
            "https://github.com/malcommac/SwiftLocation",
            "https://github.com/SVProgressHUD/SVProgressHUD",
            "https://github.com/ninjaprox/NVActivityIndicatorView",
            "https://github.com/hackiftekhar/IQKeyboardManager",
            "https://github.com/matteocrippa/awesome-swift",
            "https://github.com/dkhamsing/open-source-ios-apps",
            "https://github.com/Quick/Quick",
            "https://github.com/Quick/Nimble",
            "https://github.com/AFNetworking/AFNetworking",
            "https://github.com/rileytestut/Roxas",
            "https://github.com/ashleymills/Reachability.swift",
            "https://github.com/soffes/Cache",
            "https://github.com/JohnSundell/Ink",
            "https://github.com/JohnSundell/Publish",
            "https://github.com/JohnSundell/Plot",
            "https://github.com/JohnSundell/Files",
            "https://github.com/JohnSundell/ShellOut",
            "https://github.com/JohnSundell/Splash",
            "https://github.com/JohnSundell/Sweep",
            "https://github.com/JohnSundell/Codextended",
            "https://github.com/JohnSundell/CollectionConcurrencyKit",
            "https://github.com/httpswift/swifter",
            "https://github.com/Swinject/Swinject",
            "https://github.com/uber/needle",
            "https://github.com/google/GoogleSignIn-iOS",
            "https://github.com/openid/AppAuth-iOS",
            "https://github.com/MobileNativeFoundation/Kronos",
            "https://github.com/lyft/Kronos",
            "https://github.com/marmelroy/PhoneNumberKit",
            "https://github.com/marmelroy/Zip",
            "https://github.com/weichsel/ZIPFoundation",
            "https://github.com/mattt/Surge",
            "https://github.com/hollance/Matft",
            "https://github.com/devxoul/Then",
            "https://github.com/devxoul/URLNavigator",
            "https://github.com/ReactorKit/ReactorKit",
            "https://github.com/Carthage/Carthage",
            "https://github.com/CocoaPods/CocoaPods",
            "https://github.com/realm/jazzy",
            "https://github.com/marmelroy/Localize-Swift",
            "https://github.com/vapor/jwt-kit",
            "https://github.com/vapor/redis",
            "https://github.com/vapor/queues",
            "https://github.com/vapor/leaf",
            "https://github.com/vapor/websocket-kit",
            "https://github.com/vapor/async-kit",
            "https://github.com/vapor/multipart-kit",
            "https://github.com/vapor/routing-kit",
            "https://github.com/apollographql/apollo-ios",
            "https://github.com/stencilproject/Stencil",
            "https://github.com/jpsim/Yams",
            "https://github.com/Flight-School/AnyCodable",
            "https://github.com/danielgindi/Charts",
            "https://github.com/drmohundro/SWXMLHash",
            "https://github.com/Juanpe/SkeletonView",
            "https://github.com/intitni/CopilotForXcode",
            "https://github.com/pvieito/PythonKit",
            "https://github.com/Cocoanetics/DTCoreText",
            "https://github.com/slackhq/PanModal",
            "https://github.com/slackhq/Nebula",
            "https://github.com/mkrd/Swift-Big-Integer",
            "https://github.com/NikolaiRuhe/NRFoundation",
        ]
        for c in curated:
            if c not in names:
                names.append(c)
    log.info(f"[swift] collected {len(names)} candidates")
    return names


async def list_pub(session) -> list[str]:
    """pub.dev top packages by popularity."""
    names: list[str] = []
    # pub.dev search API with popularity ordering
    for page in range(1, 20):
        url = f"https://pub.dev/api/search?q=&sort=popularity&page={page}"
        try:
            async with session.get(url, timeout=HTTP_TIMEOUT, headers=HEADERS) as r:
                if r.status != 200:
                    break
                data = await r.json(content_type=None)
                pkgs = data.get("packages", [])
                if not pkgs:
                    break
                for p in pkgs:
                    n = p.get("package") if isinstance(p, dict) else p
                    if n and n not in names:
                        names.append(n)
        except Exception as e:
            log.warning(f"pub page {page}: {e}")
            break
        await asyncio.sleep(0.5)
    log.info(f"[pub] collected {len(names)} candidates")
    return names


async def list_hex(session) -> list[str]:
    """Hex.pm top by total downloads."""
    names: list[str] = []
    for page in range(1, 10):
        url = f"https://hex.pm/api/packages?sort=total_downloads&per_page=100&page={page}"
        try:
            async with session.get(url, timeout=HTTP_TIMEOUT, headers=HEADERS) as r:
                if r.status != 200:
                    break
                data = await r.json(content_type=None)
                if not data:
                    break
                for p in data:
                    n = p.get("name")
                    if n and n not in names:
                        names.append(n)
        except Exception as e:
            log.warning(f"hex page {page}: {e}")
            break
        await asyncio.sleep(0.5)
    log.info(f"[hex] collected {len(names)} candidates")
    return names


async def list_homebrew(session) -> list[str]:
    """Homebrew all formulae, sorted by 30d installs."""
    names: list[str] = []
    url = "https://formulae.brew.sh/api/formula.json"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=60), headers=HEADERS) as r:
            if r.status == 200:
                data = await r.json(content_type=None)
                # Each entry has analytics.install.30d when available
                entries = []
                for f in data:
                    n = f.get("name")
                    installs = 0
                    try:
                        installs = f.get("analytics", {}).get("install", {}).get("30d", {}).get(n, 0) or 0
                    except Exception:
                        installs = 0
                    entries.append((n, installs))
                entries.sort(key=lambda e: -(e[1] or 0))
                popular = [
                    'git','node','python','python@3.12','python@3.11','wget','curl','vim','neovim','tmux','htop','jq',
                    'ffmpeg','imagemagick','redis','postgresql@16','mysql','sqlite','nginx','httpd','go','rust',
                    'ruby','openjdk','gradle','maven','kotlin','scala','php','composer','ruby-build','rbenv',
                    'pyenv','nvm','yarn','pnpm','bun','deno','docker','kubectl','helm','k9s','terraform','awscli',
                    'gcloud','azure-cli','gh','lazygit','hugo','pandoc','fd','ripgrep','bat','fzf','exa','eza',
                    'tree','zsh','bash','fish','starship','neofetch','cmake','ninja','make','autoconf','libtool',
                    'pkg-config','openssl','libssh2','libgit2','icu4c','readline','ncurses','zstd','lz4','xz','bzip2',
                    'gzip','tar','zip','unzip','p7zip','rsync','wget2','axel','aria2','mosh','openssh','gnupg','pinentry',
                    'age','restic','borgbackup','duplicity','rclone','mc','ranger','nnn','bpytop','bottom','btop',
                    'glances','iftop','nethogs','nmap','netcat','socat','tcpdump','wireshark','mtr','iperf3',
                ]
                pop_names = set(e[0] for e in entries if e[0] in popular)
                ranked = [p for p in popular if p in pop_names]
                rest = [e[0] for e in entries if e[0] and e[0] not in pop_names]
                names = ranked + rest
    except Exception as e:
        log.warning(f"homebrew: {e}")
    log.info(f"[homebrew] collected {len(names)} candidates")
    return names


async def list_hackage(session) -> list[str]:
    """Hackage preferred versions — list all names."""
    names: list[str] = []
    url = "https://hackage.haskell.org/packages/"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=60),
                               headers={**HEADERS, "Accept": "application/json"}) as r:
            if r.status == 200:
                data = await r.json(content_type=None)
                for p in data:
                    n = p.get("packageName")
                    if n:
                        names.append(n)
    except Exception as e:
        log.warning(f"hackage list: {e}")
    # Try to prioritize by downloads
    ranked: list[str] = []
    try:
        url2 = "https://hackage.haskell.org/packages/top"
        async with session.get(url2, timeout=aiohttp.ClientTimeout(total=30),
                               headers={**HEADERS, "Accept": "application/json"}) as r:
            if r.status == 200:
                txt = await r.text()
                # top page is HTML — extract package names (simplistic)
                import re
                for m in re.finditer(r'/package/([A-Za-z0-9\-\_]+)"', txt):
                    if m.group(1) not in ranked:
                        ranked.append(m.group(1))
    except Exception:
        pass
    # Merge: ranked first, then rest
    result = []
    seen = set()
    for n in ranked + names:
        if n not in seen:
            seen.add(n)
            result.append(n)
    log.info(f"[hackage] collected {len(result)} candidates (ranked={len(ranked)})")
    return result


async def list_cpan(session) -> list[str]:
    """MetaCPAN top releases."""
    names: list[str] = []
    # Authoritative: popular releases
    query = {
        "size": 500,
        "_source": ["distribution"],
        "sort": [{"stat.mtime": "desc"}],
        "query": {"term": {"status": "latest"}},
    }
    import json as _json
    url = "https://fastapi.metacpan.org/v1/release/_search"
    try:
        async with session.post(url, data=_json.dumps(query),
                                headers={**HEADERS, "Content-Type": "application/json"},
                                timeout=aiohttp.ClientTimeout(total=30)) as r:
            if r.status == 200:
                data = await r.json(content_type=None)
                for h in data.get("hits", {}).get("hits", []):
                    dist = h.get("_source", {}).get("distribution")
                    if dist and dist not in names:
                        names.append(dist)
    except Exception as e:
        log.warning(f"cpan popular: {e}")

    # Add common set
    if len(names) < 300:
        for q in ["Moose", "DBIx", "Catalyst", "Mojolicious", "LWP", "JSON", "Test", "DateTime"]:
            try:
                url = f"https://fastapi.metacpan.org/v1/release/_search?q=distribution:{q}*&size=100"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15), headers=HEADERS) as r:
                    if r.status == 200:
                        data = await r.json(content_type=None)
                        for h in data.get("hits", {}).get("hits", []):
                            dist = h.get("_source", {}).get("distribution")
                            if dist and dist not in names:
                                names.append(dist)
            except Exception:
                pass
            await asyncio.sleep(0.5)
    log.info(f"[cpan] collected {len(names)} candidates")
    return names


async def list_cran(session) -> list[str]:
    """CRAN all packages (via crandb)."""
    names: list[str] = []
    url = "https://crandb.r-pkg.org/-/latest?limit=2000"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=60), headers=HEADERS) as r:
            if r.status == 200:
                data = await r.json(content_type=None)
                if isinstance(data, dict):
                    for k in data.keys():
                        names.append(k)
                elif isinstance(data, list):
                    for p in data:
                        n = p.get("Package") if isinstance(p, dict) else p
                        if n:
                            names.append(n)
    except Exception as e:
        log.warning(f"cran: {e}")
    # Prioritize popular ones
    popular = [
        "ggplot2", "dplyr", "tidyr", "readr", "purrr", "tibble", "stringr", "forcats",
        "lubridate", "broom", "Rcpp", "data.table", "magrittr", "knitr", "rmarkdown",
        "shiny", "shinydashboard", "shinyjs", "DT", "plotly", "leaflet", "highcharter",
        "caret", "randomForest", "xgboost", "glmnet", "e1071", "nnet", "MASS",
        "tidyverse", "janitor", "scales", "gtable", "gridExtra", "cowplot", "patchwork",
        "viridis", "RColorBrewer", "corrplot", "car", "lme4", "nlme", "survival",
        "forecast", "tseries", "zoo", "xts", "quantmod", "PerformanceAnalytics",
        "httr", "httr2", "jsonlite", "rvest", "curl", "xml2", "openssl",
        "DBI", "RSQLite", "RPostgres", "RMySQL", "odbc", "pool",
        "devtools", "usethis", "roxygen2", "testthat", "covr", "renv", "remotes",
        "pkgdown", "sessioninfo", "rlang", "cli", "glue", "fs", "withr",
        "future", "furrr", "foreach", "doParallel", "parallel",
        "reticulate", "keras", "tensorflow", "torch",
    ]
    ranked = [p for p in popular if p in names]
    rest = [p for p in names if p not in ranked]
    result = ranked + rest
    log.info(f"[cran] collected {len(result)} candidates (popular={len(ranked)})")
    return result


async def list_conda(session) -> list[str]:
    """conda-forge top packages."""
    names: list[str] = []
    # Use anaconda.org API
    for offset in range(0, 2000, 100):
        url = f"https://api.anaconda.org/packages/search?channel=conda-forge&sort=-downloads&limit=100&offset={offset}"
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=20), headers=HEADERS) as r:
                if r.status != 200:
                    break
                data = await r.json(content_type=None)
                if not data:
                    break
                for p in data:
                    n = p.get("name")
                    if n and n not in names:
                        names.append(n)
                if len(data) < 100:
                    break
        except Exception as e:
            log.warning(f"conda offset {offset}: {e}")
            break
        await asyncio.sleep(0.5)

    # Fallback curated popular
    if len(names) < 300:
        fallback = [
            "numpy", "scipy", "pandas", "matplotlib", "scikit-learn", "seaborn", "statsmodels",
            "jupyter", "jupyterlab", "notebook", "ipython", "ipywidgets",
            "pytorch", "torchvision", "tensorflow", "keras", "transformers",
            "xgboost", "lightgbm", "catboost",
            "requests", "urllib3", "aiohttp", "httpx", "fastapi", "uvicorn", "flask", "django",
            "sqlalchemy", "psycopg2", "pymongo", "redis-py", "pymysql",
            "pillow", "opencv", "scikit-image", "imageio",
            "pyyaml", "toml", "lxml", "beautifulsoup4", "selenium", "scrapy",
            "pytest", "black", "flake8", "mypy", "ruff", "pylint", "pre-commit",
            "conda", "pip", "setuptools", "wheel", "virtualenv", "poetry",
            "dask", "polars", "pyarrow", "numba", "cython",
            "plotly", "bokeh", "altair", "folium",
            "networkx", "igraph", "graph-tool",
            "sympy", "mpmath", "gmpy2",
            "boto3", "google-cloud-storage", "azure-storage-blob",
            "click", "typer", "rich", "tqdm",
        ]
        for f in fallback:
            if f not in names:
                names.append(f)
    log.info(f"[conda] collected {len(names)} candidates")
    return names


async def list_cocoapods(session) -> list[str]:
    """CocoaPods trunk — top pods."""
    names: list[str] = []
    # Try trunk API (limited)
    url = "https://trunk.cocoapods.org/api/v1/pods/stats"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15), headers=HEADERS) as r:
            if r.status == 200:
                data = await r.json(content_type=None)
                for p in (data or []):
                    n = p.get("name") if isinstance(p, dict) else p
                    if n:
                        names.append(n)
    except Exception:
        pass

    # CocoaPods search
    for q in ["", "a", "e", "i", "o", "u", "s", "n", "r"]:
        try:
            url = f"https://cocoapods.org/search.json?query={q}&per_page=100"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15), headers=HEADERS) as r:
                if r.status == 200:
                    data = await r.json(content_type=None)
                    items = data if isinstance(data, list) else data.get("results", [])
                    for p in items:
                        n = p.get("name") if isinstance(p, dict) else p
                        if n and n not in names:
                            names.append(n)
        except Exception:
            pass
        await asyncio.sleep(0.5)

    # Fallback curated
    curated = [
        "Alamofire", "SnapKit", "Kingfisher", "SwiftyJSON", "AFNetworking",
        "RxSwift", "RxCocoa", "ReactiveCocoa", "PromiseKit",
        "Realm", "RealmSwift", "SQLite.swift", "GRDB.swift",
        "Firebase", "FirebaseAuth", "FirebaseFirestore", "FirebaseAnalytics",
        "FirebaseCore", "FirebaseDatabase", "FirebaseMessaging", "FirebaseCrashlytics",
        "Sentry", "Mixpanel", "Amplitude", "Bugsnag",
        "Lottie", "SDWebImage", "Nuke", "YYImage", "FLAnimatedImage",
        "MBProgressHUD", "SVProgressHUD", "JGProgressHUD", "NVActivityIndicatorView",
        "IQKeyboardManager", "IQKeyboardManagerSwift", "KeychainAccess",
        "Moya", "Starscream", "SocketRocket", "SocketIO-Client-Swift",
        "Charts", "Cards", "Hero", "Material-Components",
        "CryptoSwift", "RNCryptor", "OpenSSL",
        "SwiftSoup", "Kanna", "Ono",
        "SwiftLint", "SwiftFormat", "OCLint",
        "Reachability", "ReachabilitySwift",
        "Bolts", "AsyncDisplayKit", "Texture", "IGListKit",
        "MonkeyKing", "DZNEmptyDataSet",
        "BPXLUUIDHandler", "ObjectMapper", "Mantle",
        "AppAuth", "OAuthSwift", "GoogleSignIn", "FBSDKLoginKit",
        "Stripe", "Braintree", "AdyenCard", "PayPal-Mobile",
        "Branch", "Adjust", "AppsFlyerFramework",
        "Zendesk", "Freshchat", "Intercom", "Crisp-SDK",
        "AWSCore", "AWSS3", "AWSDynamoDB", "AWSCognito",
        "PocketSVG", "Macaw", "PaintCode",
        "MessageKit", "JSQMessagesViewController",
        "CocoaLumberjack", "XCGLogger", "SwiftyBeaver", "Willow",
        "Quick", "Nimble", "OCMock", "OHHTTPStubs",
        "HanekeSwift", "PINCache", "TMCache",
    ]
    for c in curated:
        if c not in names:
            names.append(c)
    log.info(f"[cocoapods] collected {len(names)} candidates")
    return names


LIST_FNS = {
    "maven": list_maven,
    "go": list_go,
    "swift": list_swift,
    "pub": list_pub,
    "hex": list_hex,
    "homebrew": list_homebrew,
    "hackage": list_hackage,
    "cpan": list_cpan,
    "cran": list_cran,
    "conda": list_conda,
    "cocoapods": list_cocoapods,
}


async def get_current_counts() -> dict[str, int]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT ecosystem, COUNT(*) c FROM packages GROUP BY ecosystem")
    return {r["ecosystem"]: r["c"] for r in rows}


async def existing_names(eco: str) -> set[str]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT name FROM packages WHERE ecosystem=$1", eco)
    return {r["name"] for r in rows}


async def process_one(eco: str, name: str) -> bool:
    """Fetch + score + save single package. Returns True if saved (and metadata is real)."""
    try:
        pkg = await fetch_package(eco, name)
        if not pkg:
            return False
        # Require actual metadata — no fake filler
        has_real = any([
            pkg.get("latest_version"),
            pkg.get("description"),
            pkg.get("homepage"),
            pkg.get("repository"),
        ])
        if not has_real:
            return False
        latest = pkg.get("latest_version") or ""
        try:
            vulns = await fetch_vulnerabilities(eco, name, latest_version=latest)
        except Exception:
            vulns = []
        try:
            health = calculate_health_score(pkg, vulns)
            hscore = health.get("score", 0) if isinstance(health, dict) else 0
        except Exception:
            hscore = 0
        await save_package_to_db(pkg, hscore, vulns or [])
        try:
            await cache_set(f"check:{eco}:{name}", {
                "package": name, "ecosystem": eco,
                "latest_version": pkg.get("latest_version"),
                "health": health if isinstance(health, dict) else {"score": hscore},
                "vulnerabilities": {"count": len(vulns or [])},
            }, ttl=86400)
        except Exception:
            pass
        return True
    except Exception as e:
        log.debug(f"  ! {eco}:{name} -> {e}")
        return False


async def populate_ecosystem(eco: str, target: int, session) -> tuple[int, int]:
    """Returns (saved_count_delta, attempts)."""
    start = time.time()
    log.info(f"=== {eco} target={target} ===")
    existing = await existing_names(eco)
    log.info(f"[{eco}] already in DB: {len(existing)}")
    if len(existing) >= target:
        log.info(f"[{eco}] already at/above target, skip")
        return (0, 0)

    try:
        candidates = await LIST_FNS[eco](session)
    except Exception as e:
        log.error(f"[{eco}] list builder failed: {e}")
        return (0, 0)

    # Filter out already-present
    todo = [n for n in candidates if n not in existing]
    log.info(f"[{eco}] candidates={len(candidates)} todo={len(todo)}")
    need = target - len(existing)

    saved = 0
    attempts = 0
    for n in todo:
        if saved >= need:
            break
        if time.time() - start > MAX_REGISTRY_SECONDS:
            log.warning(f"[{eco}] registry time budget reached, stop")
            break
        attempts += 1
        ok = await process_one(eco, n)
        if ok:
            saved += 1
            if saved % 25 == 0:
                log.info(f"[{eco}] progress {saved}/{need} (tried {attempts})")
        # rate-limit: 1s same registry
        await asyncio.sleep(1.0)

    elapsed = time.time() - start
    log.info(f"[{eco}] DONE saved={saved} attempts={attempts} in {elapsed:.0f}s")
    return (saved, attempts)


async def main():
    run_start = time.time()
    log.info("================ MASS POPULATE START ================")
    counts_before = await get_current_counts()
    log.info(f"Before: {counts_before}")

    order = ["maven", "go", "swift", "pub", "hex", "homebrew",
             "hackage", "cpan", "cran", "conda", "cocoapods"]

    results: dict[str, tuple[int, int]] = {}
    async with aiohttp.ClientSession() as session:
        for eco in order:
            if time.time() - run_start > MAX_RUN_SECONDS:
                log.warning("Global time budget reached, stopping early")
                break
            target = TARGETS[eco]
            try:
                saved, attempts = await populate_ecosystem(eco, target, session)
                results[eco] = (saved, attempts)
            except Exception as e:
                log.error(f"[{eco}] fatal: {e}")
                results[eco] = (0, 0)
            # small pause between registries
            await asyncio.sleep(2.0)

    counts_after = await get_current_counts()
    log.info("================ MASS POPULATE DONE ================")
    log.info(f"Duration: {(time.time()-run_start)/60:.1f}min")
    log.info(f"Before:  {counts_before}")
    log.info(f"After:   {counts_after}")
    for eco in order:
        b = counts_before.get(eco, 0)
        a = counts_after.get(eco, 0)
        d = a - b
        tgt = TARGETS[eco]
        status = "OK" if a >= tgt else "PARTIAL"
        log.info(f"  {eco:12s} {b:5d} -> {a:5d}  (+{d:4d})  target={tgt}  [{status}]")


if __name__ == "__main__":
    asyncio.run(main())
