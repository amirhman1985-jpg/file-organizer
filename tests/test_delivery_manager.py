import base64
import json
import zipfile

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from file_organizer import license as license_module
from file_organizer.license import load_license
from tools import delivery_manager


def prepare_license(
    tmp_path,
    monkeypatch,
):
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    public_key_b64 = base64.b64encode(
        public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    ).decode("ascii")

    private_key_path = (
        tmp_path / "license_private.key"
    )

    private_key_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )

    monkeypatch.setattr(
        license_module,
        "PUBLIC_KEY_B64",
        public_key_b64,
    )

    monkeypatch.setattr(
        "tools.license_manager.PRIVATE_KEY_PATH",
        private_key_path,
    )

    from tools.license_manager import issue_license

    license_dir = (
        tmp_path / "licenses" / "active"
    )
    license_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    monkeypatch.setattr(
        "tools.license_manager.ACTIVE_DIR",
        license_dir,
    )

    license_path = issue_license(
        license_id="FOP-TEST-DELIVERY",
        order_id="ORD-TEST-DELIVERY",
        customer="Amir",
        customer_email="amir@example.com",
    )

    return license_path


def create_test_pro_zip(
    tmp_path,
):
    package_root = (
        tmp_path
        / "FileOrganizer-Pro-v0.3.1-Windows-x64"
    )

    package_root.mkdir()

    (package_root / "FileOrganizerPro.exe").write_bytes(
        b"test-executable"
    )

    (package_root / "config.json").write_text(
        "{}",
        encoding="utf-8",
    )

    zip_path = (
        tmp_path
        / "FileOrganizer-Pro-v0.3.1-Windows-x64.zip"
    )

    with zipfile.ZipFile(
        zip_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        for path in package_root.rglob("*"):
            if path.is_file():
                archive.write(
                    path,
                    path.relative_to(tmp_path),
                )

    return zip_path


def test_create_customer_package(
    tmp_path,
    monkeypatch,
):
    license_path = prepare_license(
        tmp_path,
        monkeypatch,
    )

    pro_zip = create_test_pro_zip(
        tmp_path
    )

    output_dir = (
        tmp_path / "deliveries"
    )

    output = (
        delivery_manager.create_customer_package(
            pro_zip_path=pro_zip,
            license_path=license_path,
            customer="Amir",
            output_dir=output_dir,
        )
    )

    assert output.exists()
    assert output.parent == output_dir

    with zipfile.ZipFile(
        output,
        "r",
    ) as archive:
        names = archive.namelist()

        license_names = [
            name
            for name in names
            if name.endswith(
                "/license.json"
            )
            or name == "license.json"
        ]

        assert len(license_names) == 1

        license_name = license_names[0]

        extracted_license = json.loads(
            archive.read(
                license_name
            ).decode("utf-8")
        )

    assert (
        extracted_license["license_id"]
        == "FOP-TEST-DELIVERY"
    )

    assert (
        extracted_license["order_id"]
        == "ORD-TEST-DELIVERY"
    )

    assert (
        extracted_license["customer"]
        == "Amir"
    )

    assert (
        extracted_license["publisher"]
        == "TechYarman"
    )


def test_customer_license_in_package_is_valid(
    tmp_path,
    monkeypatch,
):
    license_path = prepare_license(
        tmp_path,
        monkeypatch,
    )

    pro_zip = create_test_pro_zip(
        tmp_path
    )

    output = (
        delivery_manager.create_customer_package(
            pro_zip_path=pro_zip,
            license_path=license_path,
            customer="Amir",
            output_dir=tmp_path / "deliveries",
        )
    )

    extract_dir = (
        tmp_path / "extracted"
    )

    with zipfile.ZipFile(
        output,
        "r",
    ) as archive:
        archive.extractall(
            extract_dir
        )

    extracted_license_files = list(
        extract_dir.rglob(
            "license.json"
        )
    )

    assert len(extracted_license_files) == 1

    extracted_license = (
        extracted_license_files[0]
    )

    result = load_license(
        extracted_license
    )

    assert result.license_id == (
        "FOP-TEST-DELIVERY"
    )

    assert result.order_id == (
        "ORD-TEST-DELIVERY"
    )

    assert result.customer == "Amir"
    assert result.product == "File Organizer"
    assert result.publisher == "TechYarman"


def test_public_pro_zip_is_not_modified(
    tmp_path,
    monkeypatch,
):
    license_path = prepare_license(
        tmp_path,
        monkeypatch,
    )

    pro_zip = create_test_pro_zip(
        tmp_path
    )

    original_bytes = pro_zip.read_bytes()

    delivery_manager.create_customer_package(
        pro_zip_path=pro_zip,
        license_path=license_path,
        customer="Amir",
        output_dir=tmp_path / "deliveries",
    )

    assert pro_zip.read_bytes() == (
        original_bytes
    )


def test_customer_name_is_safe_for_filename(
    tmp_path,
    monkeypatch,
):
    license_path = prepare_license(
        tmp_path,
        monkeypatch,
    )

    pro_zip = create_test_pro_zip(
        tmp_path
    )

    output = (
        delivery_manager.create_customer_package(
            pro_zip_path=pro_zip,
            license_path=license_path,
            customer="Amir Ahmadi / Test",
            output_dir=tmp_path / "deliveries",
        )
    )

    assert output.exists()
    assert "/" not in output.name
    assert "\\" not in output.name