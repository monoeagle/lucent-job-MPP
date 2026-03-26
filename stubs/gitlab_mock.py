import os
from datetime import datetime, timezone
from flask import Flask, jsonify, request


def create_gitlab_mock_app():
    app = Flask(__name__)
    app.pipelines = {}
    app.next_pipeline_id = 1
    app.config["PIPELINE_RESULT"] = os.environ.get("GITLAB_MOCK_PIPELINE_RESULT", "success")

    @app.route("/api/v4/projects/<int:project_id>/trigger/pipeline", methods=["POST"])
    def trigger_pipeline(project_id):
        body = request.get_json(silent=True) or {}
        token = body.get("token")
        if not token:
            return jsonify({"message": "401 Unauthorized"}), 401

        ref = body.get("ref", "main")
        variables = body.get("variables", {})

        pipeline_id = app.next_pipeline_id
        app.next_pipeline_id += 1

        now = datetime.now(timezone.utc).isoformat()
        pipeline = {
            "id": pipeline_id,
            "project_id": project_id,
            "ref": ref,
            "status": "pending",
            "created_at": now,
            "finished_at": None,
            "duration": None,
            "variables": variables,
            "status_history": [{"status": "pending", "timestamp": now}],
        }
        app.pipelines[pipeline_id] = pipeline

        return jsonify({
            "id": pipeline_id,
            "project_id": project_id,
            "sha": "mock-sha-" + str(pipeline_id),
            "ref": ref,
            "status": "pending",
            "created_at": now,
            "web_url": f"http://localhost:8929/stub-project/-/pipelines/{pipeline_id}",
        }), 201

    @app.route("/api/v4/projects/<int:project_id>/pipelines/<int:pipeline_id>", methods=["GET"])
    def get_pipeline(project_id, pipeline_id):
        pipeline = app.pipelines.get(pipeline_id)
        if pipeline is None:
            return jsonify({"message": "404 Not Found"}), 404
        return jsonify({
            "id": pipeline["id"],
            "project_id": pipeline["project_id"],
            "status": pipeline["status"],
            "ref": pipeline["ref"],
            "sha": "mock-sha-" + str(pipeline_id),
            "created_at": pipeline["created_at"],
            "finished_at": pipeline["finished_at"],
            "duration": pipeline["duration"],
            "web_url": f"http://localhost:8929/stub-project/-/pipelines/{pipeline_id}",
        })

    @app.route("/dev/gitlab-mock/pipelines", methods=["GET"])
    def inspect_pipelines():
        status_filter = request.args.get("status")
        pipelines = list(app.pipelines.values())
        if status_filter:
            pipelines = [p for p in pipelines if p["status"] == status_filter]
        return jsonify({"total": len(pipelines), "pipelines": pipelines})

    @app.route("/dev/gitlab-mock/pipelines", methods=["DELETE"])
    def reset_pipelines():
        app.pipelines.clear()
        app.next_pipeline_id = 1
        return jsonify({"message": "All pipeline records cleared."})

    @app.route("/dev/gitlab-mock/pipelines/<int:pipeline_id>/advance", methods=["POST"])
    def advance_pipeline(pipeline_id):
        pipeline = app.pipelines.get(pipeline_id)
        if pipeline is None:
            return jsonify({"message": "404 Not Found"}), 404

        now = datetime.now(timezone.utc).isoformat()
        current = pipeline["status"]
        result = app.config["PIPELINE_RESULT"]

        if current == "pending":
            pipeline["status"] = "running"
        elif current == "running":
            pipeline["status"] = result
            pipeline["finished_at"] = now
            pipeline["duration"] = 3
        else:
            return jsonify({"message": f"Pipeline already in terminal state: {current}"}), 409

        pipeline["status_history"].append({"status": pipeline["status"], "timestamp": now})
        return jsonify({"id": pipeline_id, "status": pipeline["status"]})

    return app


if __name__ == "__main__":
    port = int(os.environ.get("GITLAB_MOCK_PORT", "8929"))
    app = create_gitlab_mock_app()
    app.run(port=port, debug=True)
