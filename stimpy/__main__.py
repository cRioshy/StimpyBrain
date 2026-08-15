"""Run the local read-only API and the optional (disabled-by-default) observer."""
from __future__ import annotations
import signal
from threading import Event
from .app import build_app
def main():
    app=build_app(); stopped=Event()
    def request_stop(*_): stopped.set()
    signal.signal(signal.SIGINT,request_stop)
    if hasattr(signal,"SIGTERM"): signal.signal(signal.SIGTERM,request_stop)
    app["worker"].start(); app["server"].start(); app["shitzo_collector"].start(); app["social_worker"].start()
    try: stopped.wait()
    finally:
        app["social_worker"].stop(); app["shitzo_collector"].stop(); app["server"].stop(); app["worker"].stop(); app["workflow"].repository.close(); app["social_repository"].close(); app["shitzo_repository"].close(); app["store"].close()
if __name__=="__main__": main()
