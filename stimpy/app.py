"""Composition root; does not start anything on import."""
from .api import ReadOnlyAPI,StimpyApiServer
from .config import StimpyConfig
from .events import InternalEvents
from .http_client import ReadOnlyHttpClient
from .hypothesis_engine import HypothesisEngine
from .hypothesis_analysis import HypothesisAnalysisService
from .hypothesis_lifecycle import HypothesisLifecycleService
from .knowledge_graph import build_graph
from .learning_service import LearningService
from .memory_service import MemoryService
from .normalizer import ObservationNormalizer
from .observation_adapter import ObservationAdapter
from .observation_store import ObservationStore
from .offline_replay import OfflineReplayService
from .pandorick_training import PandorickTrainingService
from .worker import StimpyWorker
from .workflow_service import WorkflowService
def build_app(config=None):
    config=config or StimpyConfig.from_env(); config.validate(); store=ObservationStore(config.database_file,config.data_dir,config.jsonl_rotation_bytes); events=InternalEvents(); client=ReadOnlyHttpClient(config.pandorick_base_url,config.request_timeout_seconds,config.max_retries,config.backoff_seconds); adapter=ObservationAdapter(config,store,client,events,ObservationNormalizer(config.max_payload_bytes,config.max_future_skew_seconds)); memory=MemoryService(store,events); learning=LearningService(memory); workflow=WorkflowService(config.database_file); hypothesis_engine=HypothesisEngine(store,config.hypothesis_min_investigating_cases,config.hypothesis_min_provisional_cases,config.hypothesis_min_supported_cases,config.hypothesis_min_supported_ratio,config.hypothesis_max_contradicted_ratio,config.hypothesis_max_text_chars); hypothesis_analysis=HypothesisAnalysisService(store,hypothesis_engine,config.incubation_default_seconds,config.incubation_max_retries); hypothesis_lifecycle=HypothesisLifecycleService(store,config.hypothesis_max_text_chars); offline_replay=OfflineReplayService(store); pandorick_training=PandorickTrainingService(store); worker=StimpyWorker(config,adapter,store,memory,workflow); api=ReadOnlyAPI(store,memory,learning,build_graph,worker); server=StimpyApiServer(api,config.api_host,config.api_port); return {"config":config,"store":store,"events":events,"adapter":adapter,"memory":memory,"learning":learning,"hypothesis_engine":hypothesis_engine,"hypothesis_analysis":hypothesis_analysis,"hypothesis_lifecycle":hypothesis_lifecycle,"offline_replay":offline_replay,"pandorick_training":pandorick_training,"workflow":workflow,"worker":worker,"api":api,"server":server}
