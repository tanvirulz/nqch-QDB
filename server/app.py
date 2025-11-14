import argparse, base64
from flask import Flask, request, jsonify
from sqlalchemy import select, desc
from .config import Config
from .db import make_engine, make_session_factory
from .models import Base, Calibration, Result,BestRun



def _check_auth(req, api_token) -> bool:
    if api_token is None:
        return True
    auth = req.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return False
    token = auth.split(" ", 1)[1].strip()
    return token == api_token

def create_app(cfg) -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = cfg.MAX_CONTENT_LENGTH

    engine = make_engine(cfg.DB_URI, echo=cfg.DEBUG)
    SessionLocal = make_session_factory(engine)
    with engine.begin() as conn:
        Base.metadata.create_all(bind=conn)

    @app.post("/bestruns/set")
    def bestruns_set():
        if not _check_auth(request, cfg.API_TOKEN):
            return jsonify({"status": "error", "error": "Unauthorized"}), 401

        payload = request.get_json(silent=True) or request.form
        calibration_hash_id = (payload.get("calibrationHashID") or "").strip()
        run_id = (payload.get("runID") or "").strip()

        if not calibration_hash_id:
            return jsonify({"status": "error", "error": "calibrationHashID is required"}), 400
        if not run_id:
            return jsonify({"status": "error", "error": "runID is required"}), 400

        try:
            with SessionLocal() as ses:
                row = BestRun(
                    calibration_hash_id=calibration_hash_id,
                    run_id=run_id,
                )
                ses.add(row)
                ses.commit()
                ses.refresh(row)

                return jsonify({
                    "status": "ok",
                    "id": row.id,
                    "calibration_hash_id": row.calibration_hash_id,
                    "run_id": row.run_id,
                    "created_at": str(row.created_at),
                })
        except Exception as e:
            return jsonify({"status": "error", "error": str(e)}), 500
    
    @app.get("/bestruns/get")
    def bestruns_get():
        if not _check_auth(request, cfg.API_TOKEN):
            return jsonify({"status": "error", "error": "Unauthorized"}), 401

        with SessionLocal() as ses:
            row = ses.execute(
                select(BestRun)
                .order_by(desc(BestRun.id))
                .limit(1)
            ).scalar_one_or_none()

            if row is None:
                return jsonify({"status": "error", "error": "no best run set"}), 404

            return jsonify({
                "status": "ok",
                "id": row.id,
                "calibration_hash_id": row.calibration_hash_id,
                "run_id": row.run_id,
                "created_at": str(row.created_at),
            })
    @app.get("/bestruns/list")
    def bestruns_list():
        if not _check_auth(request, cfg.API_TOKEN):
            return jsonify({"status": "error", "error": "Unauthorized"}), 401

        # optional ?limit=N, default 10
        raw_limit = request.args.get("limit", "").strip()
        try:
            limit = int(raw_limit) if raw_limit else 10
        except ValueError:
            return jsonify({"status": "error", "error": "limit must be an integer"}), 400

        # safety clamp
        if limit <= 0:
            limit = 1
        if limit > 100:
            limit = 100

        with SessionLocal() as ses:
            rows = ses.execute(
                select(BestRun)
                .order_by(desc(BestRun.id))
                .limit(limit)
            ).scalars().all()

            items = [
                {
                    "id": r.id,
                    "calibration_hash_id": r.calibration_hash_id,
                    "run_id": r.run_id,
                    "created_at": str(r.created_at),
                }
                for r in rows
            ]

            return jsonify({
                "status": "ok",
                "items": items,
            })

    @app.post("/calibrations/upload")
    def cal_upload():
        if not _check_auth(request, cfg.API_TOKEN):
            return jsonify({"status": "error", "error": "Unauthorized"}), 401
        hash_id = (request.form.get("hashID") or "").strip()
        notes = (request.form.get("notes") or "").strip()
        file = request.files.get("archive")
        if not hash_id:
            return jsonify({"status": "error", "error": "hashID is required"}), 400
        if not file or file.filename == "":
            return jsonify({"status": "error", "error": "archive file is required"}), 400
        data = file.read()
        try:
            with SessionLocal() as ses:
                row = Calibration(hash_id=hash_id, notes=notes or None, filename=file.filename, data=data)
                ses.add(row); ses.commit(); ses.refresh(row)
                return jsonify({"status": "ok", "id": row.id, "created_at": str(row.created_at)})
        except Exception as e:
            return jsonify({"status": "error", "error": str(e)}), 500

    @app.get("/calibrations/list")
    def cal_list():
        if not _check_auth(request, cfg.API_TOKEN):
            return jsonify({"status": "error", "error": "Unauthorized"}), 401
        with SessionLocal() as ses:
            rows = ses.execute(select(Calibration).order_by(desc(Calibration.created_at))).scalars().all()
            items = [{
                "id": r.id, "hashID": r.hash_id, "notes": r.notes,
                "created_at": str(r.created_at), "filename": r.filename, "size": len(r.data) if r.data else 0
            } for r in rows]
            return jsonify({"items": items})

    @app.get("/calibrations/latest")
    def cal_latest():
        if not _check_auth(request, cfg.API_TOKEN):
            return jsonify({"status": "error", "error": "Unauthorized"}), 401
        with SessionLocal() as ses:
            r = ses.execute(select(Calibration).order_by(desc(Calibration.created_at)).limit(1)).scalar_one_or_none()
            if not r:
                return jsonify({"error": "no calibrations"}), 404
            return jsonify({"hashID": r.hash_id, "notes": r.notes, "created_at": str(r.created_at)})

    @app.post("/calibrations/download")
    def cal_download():
        if not _check_auth(request, cfg.API_TOKEN):
            return jsonify({"status": "error", "error": "Unauthorized"}), 401
        payload = request.get_json(silent=True) or request.form
        hash_id = (payload.get("hashID") or "").strip()
        if not hash_id:
            return jsonify({"status": "error", "error": "hashID is required"}), 400
        with SessionLocal() as ses:
            r = ses.execute(
                select(Calibration).where(Calibration.hash_id == hash_id).order_by(desc(Calibration.created_at)).limit(1)
            ).scalar_one_or_none()
            if not r:
                return jsonify({"error": "not found"}), 404
            return jsonify({
                "notes": r.notes,
                "filename": r.filename,
                "created_at": str(r.created_at),
                "data_b64": base64.b64encode(r.data).decode("ascii")
            })

    @app.post("/results/upload")
    def results_upload():
        if not _check_auth(request, cfg.API_TOKEN):
            return jsonify({"status": "error", "error": "Unauthorized"}), 401

        hash_id = (request.form.get("hashID") or "").strip()
        name = (request.form.get("name") or "").strip()
        run_id = (request.form.get("runID") or "").strip()
        notes = (request.form.get("notes") or "").strip()
        file = request.files.get("archive")

        if not hash_id:
            return jsonify({"status": "error", "error": "hashID is required"}), 400
        if not name:
            return jsonify({"status": "error", "error": "name is required"}), 400
        if not file or file.filename == "":
            return jsonify({"status": "error", "error": "archive file is required"}), 400

        data = file.read()
        try:
            with SessionLocal() as ses:
                row = Result(
                    hash_id=hash_id,
                    name=name,
                    run_id=run_id or None,
                    notes=notes or None,
                    filename=file.filename,
                    data=data,
                )
                ses.add(row)
                ses.commit()
                ses.refresh(row)

                return jsonify({
                    "status": "ok",
                    "id": row.id,
                    "created_at": str(row.created_at),
                    "run_id": row.run_id,
                })
        except Exception as e:
            return jsonify({"status": "error", "error": str(e)}), 500

    @app.get("/results/list")
    def results_list():
        if not _check_auth(request, cfg.API_TOKEN):
            return jsonify({"status": "error", "error": "Unauthorized"}), 401

        hash_id = (request.args.get("hashID") or "").strip()
        if not hash_id:
            return jsonify({"status": "error", "error": "hashID is required"}), 400

        with SessionLocal() as ses:
            rows = ses.execute(
                select(Result)
                .where(Result.hash_id == hash_id)
                .order_by(desc(Result.created_at))
            ).scalars().all()

            items = [
                {
                    "name": r.name,
                    "run_id": r.run_id,
                    "notes": r.notes,
                    "created_at": str(r.created_at),
                }
                for r in rows
            ]
            return jsonify({"items": items})

    @app.post("/results/download")
    def results_download():
        if not _check_auth(request, cfg.API_TOKEN):
            return jsonify({"status": "error", "error": "Unauthorized"}), 401

        payload = request.get_json(silent=True) or request.form
        hash_id = (payload.get("hashID") or "").strip()
        name = (payload.get("name") or "").strip()
        run_id = (payload.get("runID") or "").strip()

        if not hash_id or not name:
            return jsonify({"status": "error", "error": "hashID and name are required"}), 400

        with SessionLocal() as ses:
            stmt = select(Result).where(
                Result.hash_id == hash_id,
                Result.name == name
            )
            if run_id:
                stmt = stmt.where(Result.run_id == run_id)


            stmt = stmt.order_by(desc(Result.created_at)).limit(1)
            r = ses.execute(stmt).scalar_one_or_none()

            if not r:
                return jsonify({"error": "not found"}), 404

            return jsonify({
                "notes": r.notes,
                "filename": r.filename,
                "created_at": str(r.created_at),
                "run_id": r.run_id,
                "data_b64": base64.b64encode(r.data).decode("ascii"),
            })

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app

def create_app_from_env():
    """Gunicorn-friendly factory that loads config from env/files."""
    C = Config.load(cli_api_token=None)  # merges ENV and server config file
    return create_app(C)

def main_cli():
    parser = argparse.ArgumentParser(description="Run QIBO DB Server (Flask + SQLAlchemy).")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=5050, type=int)
    parser.add_argument("--api-token", default=None, help="Set API token and persist to server config file.")
    args = parser.parse_args()

    C = Config.load(cli_api_token=args.api_token)
    if args.api_token:
        Config.persist(api_token=args.api_token)

    app = create_app(C)
    app.run(host=args.host, port=args.port, debug=C.DEBUG)

if __name__ == "__main__":
    main_cli()
