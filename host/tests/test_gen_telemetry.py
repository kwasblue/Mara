from mara_host.tools import gen_telemetry


def test_section_items_supports_current_dataclass_schema():
    items = gen_telemetry._section_items()

    assert items
    ids = [spec["id"] for _, spec in items]
    assert ids == sorted(ids)

    imu = dict(items)["TELEM_IMU"]
    assert imu["id"] == 0x01
    assert imu["size"] == 16
    assert "ax_mg(i16)" in imu["format"]


def test_generated_python_module_contains_current_sections():
    py_code = gen_telemetry.generate_py_module()

    assert 'TELEM_IMU            = 0x01' in py_code
    assert 'TELEM_CTRL_SIGNALS   = 0x10' in py_code
    assert '"format": "ax_mg(i16)' not in py_code  # sanity: format line should include full field list, not start mid-string
    assert '"format": "online(u8) ok(u8) ax_mg(i16)' in py_code


def test_generated_cpp_header_contains_current_sections():
    cpp_code = gen_telemetry.generate_cpp_header()

    assert 'TELEM_IMU' in cpp_code
    assert '0x01' in cpp_code
    assert 'TELEM_CTRL_SIGNALS' in cpp_code
    assert 'variable' in cpp_code
