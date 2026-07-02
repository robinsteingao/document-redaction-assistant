from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .acceptance import run_acceptance_smoke
from .batch import SUPPORTED_SUFFIXES, build_batch_packages
from .commercial_package import build_commercial_install_package, validate_commercial_install_package
from .crypto import decrypt_mapping_file, encrypt_mapping_file
from .review import build_review_workspace, export_review_workspace, review_decisions_from_mapping
from .sandbox import build_sandbox_import_package
from .trial_package import build_trial_package
from .workflow import build_redaction_package, restore_text, write_package
from .desktop_shell import build_desktop_shell
from .desktop_launcher import launch_desktop_app
from .install_package import build_install_package
from .local_license import LicenseSigningKeyMissingError, validate_local_license, write_local_license
from .local_service import run_local_service
from .ocr_adapter import extract_text_with_ocr, get_ocr_status
from .offline_ocr_install import (
    build_offline_ocr_install_plan,
    validate_offline_ocr_enablement,
    write_offline_ocr_install_marker,
)
from .offline_runtime import build_ocr_wheelhouse_bundle, stage_python_runtime, validate_ocr_wheelhouse_manifest
from .pilot_feedback import build_pilot_issue_ledger
from .production_sandbox import build_production_sandbox_config, validate_production_sandbox_config
from .report_delivery import build_report_delivery_package
from .runtime_preflight import run_runtime_preflight, write_runtime_preflight_report
from .rules_update import apply_rules_update_package, validate_rules_update_package
from .open_source_preflight import run_open_source_release_preflight
from .registration import (
    RegistrationRequiredError,
    TrialLimitExceededError,
    build_registration_request,
    consume_trial_or_raise,
    registration_status,
    write_registration_request,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="document-redaction-assistant")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build-package", help="Build a local redaction upload package.")
    build.add_argument("--project-alias-id", required=True)
    build.add_argument("--out", required=True)
    build.add_argument("--customer-dictionary")
    build.add_argument("--review-decisions")
    build.add_argument("--customer-confirmed-degradation-risk", action="store_true")
    build.add_argument("--mapping-passphrase", help="Encrypt local_mapping.private.json into local_mapping.private.enc and remove the plaintext mapping.")
    build.add_argument("--registration-dir", help="Local registration directory; defaults to ~/.document_redaction_assistant")
    build.add_argument("--edition", choices=["community", "stpe_partner"], default="community")
    build.add_argument("files", nargs="+")

    review = sub.add_parser("review-workspace", help="Build local review candidates and HTML workspace.")
    review.add_argument("--project-alias-id", required=True)
    review.add_argument("--out", required=True)
    review.add_argument("--customer-dictionary")
    review.add_argument("files", nargs="+")

    restore = sub.add_parser("restore", help="Restore a redacted text/report with local mapping.")
    restore.add_argument("--mapping", required=True)
    restore.add_argument("--input", required=True)
    restore.add_argument("--output", required=True)

    batch = sub.add_parser("batch-build", help="Build packages for project directories.")
    batch.add_argument("--input-root", required=True)
    batch.add_argument("--out", required=True)
    batch.add_argument("--mapping-passphrase")
    batch.add_argument("--registration-dir", help="Local registration directory; defaults to ~/.document_redaction_assistant")
    batch.add_argument("--edition", choices=["community", "stpe_partner"], default="community")

    encrypt = sub.add_parser("encrypt-mapping", help="Encrypt and remove a local mapping JSON file.")
    encrypt.add_argument("--input", required=True)
    encrypt.add_argument("--output", required=True)
    encrypt.add_argument("--passphrase", required=True)

    decrypt = sub.add_parser("decrypt-mapping", help="Decrypt a local mapping envelope.")
    decrypt.add_argument("--input", required=True)
    decrypt.add_argument("--output", required=True)
    decrypt.add_argument("--passphrase", required=True)

    trial = sub.add_parser("build-trial-package", help="Build customer pilot documentation and sample data.")
    trial.add_argument("--out", required=True)
    trial.add_argument("--version", default="0.4.0-m4")

    install = sub.add_parser("build-install-package", help="Build a testable local installation package.")
    install.add_argument("--out", required=True)
    install.add_argument("--version", default="0.7.0-m7")
    install.add_argument("--service-url", default="http://127.0.0.1:8765")

    commercial = sub.add_parser("build-commercial-package", help="Build a complete offline commercial package when local component dirs are provided.")
    commercial.add_argument("--out", required=True)
    commercial.add_argument("--version", default="0.16.0-m16")
    commercial.add_argument("--python-runtime-dir")
    commercial.add_argument("--ocr-wheelhouse-dir")
    commercial.add_argument("--office-runtime-dir")
    commercial.add_argument("--service-url", default="http://127.0.0.1:8765")

    commercial_validate = sub.add_parser("validate-commercial-package", help="Validate a commercial offline package.")
    commercial_validate.add_argument("--package-dir", required=True)

    ocr_install_plan = sub.add_parser("build-offline-ocr-plan", help="Build an offline OCR installation plan for a commercial package app dir.")
    ocr_install_plan.add_argument("--app-dir", required=True)
    ocr_install_plan.add_argument("--engine", default="paddleocr")

    ocr_enable_validate = sub.add_parser("validate-offline-ocr", help="Validate offline OCR enablement for a commercial package app dir.")
    ocr_enable_validate.add_argument("--app-dir", required=True)

    ocr_mark = sub.add_parser("mark-offline-ocr-installed", help="Write offline OCR installed marker after local dependency installation.")
    ocr_mark.add_argument("--app-dir", required=True)
    ocr_mark.add_argument("--engine", default="paddleocr")

    shell = sub.add_parser("build-desktop-shell", help="Build a static pilot desktop shell.")
    shell.add_argument("--out", required=True)
    shell.add_argument("--version", default="0.5.0-m5")
    shell.add_argument("--service-url")

    sub.add_parser("ocr-status", help="Show optional local OCR adapter status.")

    ocr_extract = sub.add_parser("ocr-extract", help="Extract text through the optional local OCR adapter.")
    ocr_extract.add_argument("--file", required=True)

    preflight = sub.add_parser("runtime-preflight", help="Check local runtime readiness.")
    preflight.add_argument("--base-dir", default=".")
    preflight.add_argument("--output")

    preflight_os = sub.add_parser("open-source-preflight", help="Run read-only preflight checks for open-source release readiness.")
    preflight_os.add_argument("--root", default=".", help="Package root to scan (default: current directory)")
    preflight_os.add_argument("--output", help="Optional output JSON file path; if omitted, prints JSON to stdout")

    license_write = sub.add_parser("write-license", help="Write a local trial license file.")
    license_write.add_argument("--output", required=True)
    license_write.add_argument("--customer-name", default="本地试点客户")
    license_write.add_argument("--expires-on", default="2099-12-31")

    license_validate = sub.add_parser("validate-license", help="Validate a local license file.")
    license_validate.add_argument("--input", required=True)

    registration = sub.add_parser("registration-request", help="Build a local registration request. Personal registration fee: 80 CNY/year.")
    registration.add_argument("--out", required=True)
    registration.add_argument("--edition", choices=["community", "stpe_partner"], default="community")
    registration.add_argument("--email", required=True)
    registration.add_argument("--organization", default="")
    registration.add_argument("--name", default="")
    registration.add_argument("--phone", default="")
    registration.add_argument("--use-case", default="")

    trial_status = sub.add_parser("trial-status", help="Show local registration, trial quota and license status.")
    trial_status.add_argument("--registration-dir")
    trial_status.add_argument("--edition", choices=["community", "stpe_partner"], default="community")

    rules_update = sub.add_parser("apply-rules-update", help="Validate and apply an offline rules update package.")
    rules_update.add_argument("--update-dir", required=True)
    rules_update.add_argument("--active-rules-dir", required=True)

    rules_validate = sub.add_parser("validate-rules-update", help="Validate an offline rules update package.")
    rules_validate.add_argument("--update-dir", required=True)

    runtime_stage = sub.add_parser("stage-python-runtime", help="Stage a local Python executable into the runtime bundle slot.")
    runtime_stage.add_argument("--source-python", required=True)
    runtime_stage.add_argument("--runtime-dir", required=True)
    runtime_stage.add_argument("--version", default="0.12.0-m12")

    ocr_wheelhouse = sub.add_parser("build-ocr-wheelhouse", help="Build an OCR dependency wheelhouse manifest from local files.")
    ocr_wheelhouse.add_argument("--wheelhouse-dir", required=True)
    ocr_wheelhouse.add_argument("--out", required=True)
    ocr_wheelhouse.add_argument("--version", default="0.12.0-m12")

    ocr_validate = sub.add_parser("validate-ocr-wheelhouse", help="Validate an OCR wheelhouse manifest and local files.")
    ocr_validate.add_argument("--manifest", required=True)

    pilot_ledger = sub.add_parser("build-pilot-feedback-ledger", help="Build a local customer pilot issue ledger.")
    pilot_ledger.add_argument("--out", required=True)
    pilot_ledger.add_argument("--version", default="0.15.0-m15")

    sandbox_config = sub.add_parser("build-production-sandbox-config", help="Build a production sandbox import config template.")
    sandbox_config.add_argument("--out", required=True)
    sandbox_config.add_argument("--endpoint", default="http://localhost:7272/api/redaction-sandbox/import")
    sandbox_config.add_argument("--environment", default="pilot")

    sandbox_validate = sub.add_parser("validate-production-sandbox-config", help="Validate a production sandbox config template.")
    sandbox_validate.add_argument("--input", required=True)

    report_demo = sub.add_parser("build-report-delivery", help="Build a redacted report delivery package and local restore preview.")
    report_demo.add_argument("--evaluation-result", required=True)
    report_demo.add_argument("--mapping", required=True)
    report_demo.add_argument("--out", required=True)

    serve = sub.add_parser("serve-local", help="Run the local product service for the desktop shell.")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)

    acceptance = sub.add_parser("run-acceptance-smoke", help="Run repeatable local package acceptance checks.")
    acceptance.add_argument("--app-dir", default=".")
    acceptance.add_argument("--out")
    acceptance.add_argument("--project-alias-id", default="acceptance-smoke")

    launcher = sub.add_parser("launch-desktop-app", help="Start local service and open the desktop shell.")
    launcher.add_argument("--app-dir", default=".")
    launcher.add_argument("--host", default="127.0.0.1")
    launcher.add_argument("--port", type=int, default=8765)
    launcher.add_argument("--wait-seconds", type=int, default=12)

    args = parser.parse_args(argv)
    if args.command == "build-package":
        decisions = None
        if args.review_decisions:
            decisions = review_decisions_from_mapping(json.loads(Path(args.review_decisions).read_text(encoding="utf-8")))
        try:
            consume_trial_or_raise(len(args.files), edition=args.edition, registration_dir=args.registration_dir)
        except (RegistrationRequiredError, TrialLimitExceededError) as exc:
            print(str(exc))
            return 1
        package, mapping = build_redaction_package(
            args.files,
            project_alias_id=args.project_alias_id,
            customer_dictionary=args.customer_dictionary,
            review_decisions=decisions,
            customer_confirmed_degradation_risk=args.customer_confirmed_degradation_risk,
        )
        outputs = write_package(args.out, package, mapping, mapping_passphrase=args.mapping_passphrase)
        outputs.update(export_review_workspace(args.out, package, mapping))
        sandbox_path = Path(args.out) / "sandbox_import_package.json"
        sandbox_path.write_text(json.dumps(build_sandbox_import_package(package), ensure_ascii=False, indent=2), encoding="utf-8")
        outputs["sandbox_import"] = sandbox_path
        for name, path in outputs.items():
            print(f"{name}: {path}")
        return 0

    if args.command == "review-workspace":
        workspace = build_review_workspace(
            args.files,
            project_alias_id=args.project_alias_id,
            customer_dictionary=args.customer_dictionary,
        )
        output = Path(args.out)
        output.mkdir(parents=True, exist_ok=True)
        path = output / "review_workspace.json"
        path.write_text(json.dumps(workspace, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"review_workspace: {path}")
        return 0

    if args.command == "restore":
        mapping = json.loads(Path(args.mapping).read_text(encoding="utf-8"))
        redacted = Path(args.input).read_text(encoding="utf-8")
        Path(args.output).write_text(restore_text(redacted, mapping), encoding="utf-8")
        print(f"restored: {args.output}")
        return 0

    if args.command == "batch-build":
        total_files = _count_batch_files(args.input_root)
        try:
            consume_trial_or_raise(total_files, edition=args.edition, registration_dir=args.registration_dir)
        except (RegistrationRequiredError, TrialLimitExceededError) as exc:
            print(str(exc))
            return 1
        manifest = build_batch_packages(args.input_root, args.out, passphrase=args.mapping_passphrase)
        print(f"batch_manifest: {Path(args.out) / 'batch_manifest.json'}")
        print(f"project_count: {manifest['project_count']}")
        return 0

    if args.command == "encrypt-mapping":
        path = encrypt_mapping_file(args.input, args.output, passphrase=args.passphrase)
        print(f"encrypted_mapping: {path}")
        return 0

    if args.command == "decrypt-mapping":
        mapping = decrypt_mapping_file(args.input, passphrase=args.passphrase)
        Path(args.output).write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"decrypted_mapping: {args.output}")
        return 0

    if args.command == "build-trial-package":
        path = build_trial_package(args.out, version=args.version)
        print(f"trial_package: {path}")
        return 0

    if args.command == "build-install-package":
        result = build_install_package(args.out, version=args.version, service_url=args.service_url)
        print(f"install_package: {result['package_dir']}")
        print(f"archive: {result['archive']}")
        return 0

    if args.command == "build-commercial-package":
        result = build_commercial_install_package(
            args.out,
            version=args.version,
            python_runtime_dir=args.python_runtime_dir,
            ocr_wheelhouse_dir=args.ocr_wheelhouse_dir,
            office_runtime_dir=args.office_runtime_dir,
            service_url=args.service_url,
        )
        print(f"commercial_package: {result['package_dir']}")
        print(f"archive: {result['archive']}")
        return 0

    if args.command == "validate-commercial-package":
        result = validate_commercial_install_package(args.package_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "valid" else 1

    if args.command == "build-offline-ocr-plan":
        result = build_offline_ocr_install_plan(args.app_dir, engine=args.engine)
        print(f"offline_ocr_install_plan: {result['plan']}")
        print(f"offline_ocr_env: {result['env']}")
        return 0

    if args.command == "validate-offline-ocr":
        result = validate_offline_ocr_enablement(args.app_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "enabled" else 1

    if args.command == "mark-offline-ocr-installed":
        path = write_offline_ocr_install_marker(args.app_dir, engine=args.engine)
        print(f"offline_ocr_marker: {path}")
        return 0

    if args.command == "build-desktop-shell":
        path = build_desktop_shell(args.out, version=args.version, service_url=args.service_url)
        print(f"desktop_shell: {path}")
        return 0

    if args.command == "ocr-status":
        print(json.dumps(get_ocr_status(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "ocr-extract":
        print(json.dumps(extract_text_with_ocr(args.file), ensure_ascii=False, indent=2))
        return 0

    if args.command == "runtime-preflight":
        if args.output:
            path = write_runtime_preflight_report(args.output, args.base_dir)
            print(f"runtime_report: {path}")
        else:
            print(json.dumps(run_runtime_preflight(args.base_dir), ensure_ascii=False, indent=2))
        return 0

    if args.command == "open-source-preflight":
        root = Path(args.root)
        report = run_open_source_release_preflight(root)
        if args.output:
            path = Path(args.output)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"preflight_report: {path}")
        else:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["status"] == "passed" else 1

    if args.command == "write-license":
        if os.getenv("DRA_ENABLE_LICENSE_ISSUER") != "1":
            print("write-license is disabled in the public build. 请联系作者获取年度授权 license.json（个人版80元/年）。")
            return 1
        try:
            path = write_local_license(args.output, customer_name=args.customer_name, expires_on=args.expires_on)
        except LicenseSigningKeyMissingError as exc:
            print(str(exc))
            return 1
        print(f"local_license: {path}")
        return 0

    if args.command == "validate-license":
        data = json.loads(Path(args.input).read_text(encoding="utf-8"))
        result = validate_local_license(data)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "valid" else 1

    if args.command == "registration-request":
        request = build_registration_request(
            edition=args.edition,
            email=args.email,
            organization=args.organization,
            name=args.name,
            phone=args.phone,
            use_case=args.use_case,
        )
        outputs = write_registration_request(args.out, request)
        for name, path in outputs.items():
            print(f"{name}: {path}")
        print(f"annual_fee_cny: {request['annual_fee_cny']}")
        print(f"trial_file_limit: {request['trial_file_limit']}")
        return 0

    if args.command == "trial-status":
        print(json.dumps(registration_status(args.registration_dir, edition=args.edition), ensure_ascii=False, indent=2))
        return 0

    if args.command == "validate-rules-update":
        result = validate_rules_update_package(args.update_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "valid" else 1

    if args.command == "apply-rules-update":
        result = apply_rules_update_package(args.update_dir, args.active_rules_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "applied" else 1

    if args.command == "stage-python-runtime":
        result = stage_python_runtime(args.source_python, args.runtime_dir, version=args.version)
        print(f"python_exe: {result['python_exe']}")
        print(f"runtime_manifest: {result['runtime_manifest']}")
        return 0

    if args.command == "build-ocr-wheelhouse":
        result = build_ocr_wheelhouse_bundle(args.wheelhouse_dir, args.out, version=args.version)
        print(f"wheelhouse_dir: {result['wheelhouse_dir']}")
        print(f"ocr_wheelhouse_manifest: {result['ocr_wheelhouse_manifest']}")
        return 0

    if args.command == "validate-ocr-wheelhouse":
        result = validate_ocr_wheelhouse_manifest(args.manifest)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "valid" else 1

    if args.command == "build-pilot-feedback-ledger":
        result = build_pilot_issue_ledger(args.out, version=args.version)
        print(f"pilot_issue_ledger: {result['ledger_json']}")
        print(f"pilot_issue_ledger_markdown: {result['ledger_markdown']}")
        return 0

    if args.command == "build-production-sandbox-config":
        path = build_production_sandbox_config(args.out, endpoint=args.endpoint, environment=args.environment)
        print(f"production_sandbox_config: {path}")
        return 0

    if args.command == "validate-production-sandbox-config":
        result = validate_production_sandbox_config(args.input)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "valid" else 1

    if args.command == "build-report-delivery":
        evaluation_result = json.loads(Path(args.evaluation_result).read_text(encoding="utf-8-sig"))
        result = build_report_delivery_package(evaluation_result, args.mapping, args.out)
        for name, path in result.items():
            print(f"{name}: {path}")
        return 0

    if args.command == "serve-local":
        run_local_service(args.host, args.port)
        return 0

    if args.command == "run-acceptance-smoke":
        result = run_acceptance_smoke(
            args.app_dir,
            output_dir=args.out,
            project_alias_id=args.project_alias_id,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "passed" else 1

    if args.command == "launch-desktop-app":
        result = launch_desktop_app(
            args.app_dir,
            host=args.host,
            port=args.port,
            wait_seconds=args.wait_seconds,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "started" else 1

    return 2


def _count_batch_files(input_root: str | Path) -> int:
    root = Path(input_root)
    total = 0
    for project_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        total += sum(1 for p in project_dir.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES)
    return total


if __name__ == "__main__":
    raise SystemExit(main())
