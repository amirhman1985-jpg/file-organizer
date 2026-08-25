from file_organizer.ids import (
    generate_license_id,
    generate_order_id,
)


def test_order_id_format():
    order_id = generate_order_id()

    assert order_id.startswith("ORD-")
    assert len(order_id) == 17


def test_license_id_format():
    license_id = generate_license_id()

    assert license_id.startswith("FOP-")
    assert len(license_id) == 17


def test_order_ids_are_unique():
    ids = {
        generate_order_id()
        for _ in range(1000)
    }

    assert len(ids) == 1000


def test_license_ids_are_unique():
    ids = {
        generate_license_id()
        for _ in range(1000)
    }

    assert len(ids) == 1000


def test_order_and_license_ids_are_different():
    order_id = generate_order_id()
    license_id = generate_license_id()

    assert order_id != license_id