from dataclasses import dataclass

from elasticsearch import Elasticsearch

from backend.app.config import Settings


@dataclass
class AppRuntime:
    """Runtime resources initialized once and reused by application code."""

    es_client: Elasticsearch

    def close(self) -> None:
        self.es_client.close()

    def check_elasticsearch(self) -> dict[str, str]:
        info = self.es_client.info()
        return {
            "status": "ok",
            "cluster_name": str(info.get("cluster_name", "")),
            "version": str(info.get("version", {}).get("number", "")),
        }


def create_elasticsearch_client(settings: Settings) -> Elasticsearch:
    client_options: dict[str, object] = {
        "hosts": [settings.es_url],
        "basic_auth": (settings.es_username, settings.es_password),
        "request_timeout": 10,
    }

    if settings.es_ca_cert:
        client_options["ca_certs"] = settings.es_ca_cert

    return Elasticsearch(**client_options)


def create_runtime(settings: Settings) -> AppRuntime:
    return AppRuntime(es_client=create_elasticsearch_client(settings))
