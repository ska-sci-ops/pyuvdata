# -*- mode: python; coding: utf-8 -*-
# Copyright (c) 2018 Radio Astronomy Software Group
# Licensed under the 2-clause BSD License

"""Tests for uvcal object.

"""
import pytest
import os
import copy
import numpy as np

from pyuvdata import UVCal
import pyuvdata.utils as uvutils
import pyuvdata.tests as uvtest

pytestmark = pytest.mark.filterwarnings(
    "ignore:telescope_location is not set. Using known values",
    "ignore:antenna_positions is not set. Using known values",
)


@pytest.fixture(scope="function")
def uvcal_data():
    """Set up some uvcal iter tests."""
    required_properties = [
        "Nfreqs",
        "Njones",
        "Ntimes",
        "Nspws",
        "Nants_data",
        "Nants_telescope",
        "antenna_names",
        "antenna_numbers",
        "ant_array",
        "telescope_name",
        "freq_array",
        "channel_width",
        "spw_array",
        "flex_spw",
        "jones_array",
        "time_array",
        "integration_time",
        "gain_convention",
        "flag_array",
        "quality_array",
        "cal_type",
        "cal_style",
        "x_orientation",
        "future_array_shapes",
        "history",
    ]
    required_parameters = ["_" + prop for prop in required_properties]

    extra_properties = [
        "telescope_location",
        "antenna_positions",
        "lst_array",
        "gain_array",
        "delay_array",
        "sky_field",
        "sky_catalog",
        "ref_antenna_name",
        "Nsources",
        "baseline_range",
        "diffuse_model",
        "input_flag_array",
        "time_range",
        "freq_range",
        "flex_spw_id_array",
        "observer",
        "git_origin_cal",
        "git_hash_cal",
        "total_quality_array",
        "extra_keywords",
        "gain_scale",
        "filename",
    ]
    extra_parameters = ["_" + prop for prop in extra_properties]

    other_properties = ["pyuvdata_version_str"]

    uv_cal_object = UVCal()

    # yields the data we need but will continue to the del call after tests
    yield (
        uv_cal_object,
        required_parameters,
        required_properties,
        extra_parameters,
        extra_properties,
        other_properties,
    )

    # some post-test object cleanup
    del uv_cal_object
    return


@pytest.fixture
def multi_spw_gain(gain_data):
    gain_obj = gain_data.copy()
    gain_obj._set_flex_spw()
    gain_obj.channel_width = (
        np.zeros(gain_obj.Nfreqs, dtype=np.float64) + gain_obj.channel_width
    )
    gain_obj.Nspws = 2
    gain_obj.flex_spw_id_array = np.concatenate(
        (
            np.ones(gain_obj.Nfreqs // 2, dtype=int),
            np.full(gain_obj.Nfreqs // 2, 2, dtype=int),
        )
    )
    gain_obj.spw_array = np.array([1, 2])
    spw2_inds = np.nonzero(gain_obj.flex_spw_id_array == 2)[0]
    spw2_chan_width = gain_obj.channel_width[0] * 2
    gain_obj.freq_array[0, spw2_inds] = gain_obj.freq_array[
        0, spw2_inds[0]
    ] + spw2_chan_width * np.arange(spw2_inds.size)
    gain_obj.channel_width[spw2_inds] = spw2_chan_width
    gain_obj.check(check_freq_spacing=True)

    yield gain_obj

    del gain_obj


def test_parameter_iter(uvcal_data):
    """Test expected parameters."""
    (
        uv_cal_object,
        required_parameters,
        required_properties,
        extra_parameters,
        extra_properties,
        other_properties,
    ) = uvcal_data
    all_params = []
    for prop in uv_cal_object:
        all_params.append(prop)
    for a in required_parameters + extra_parameters:
        assert a in all_params, (
            "expected attribute " + a + " not returned in object iterator"
        )


def test_required_parameter_iter(uvcal_data):
    """Test expected required parameters."""
    (
        uv_cal_object,
        required_parameters,
        required_properties,
        extra_parameters,
        extra_properties,
        other_properties,
    ) = uvcal_data
    # at first it's a metadata_only object, so need to modify required_parameters
    required = []
    for prop in uv_cal_object.required():
        required.append(prop)
    expected_required = copy.copy(required_parameters)
    expected_required.remove("_quality_array")
    expected_required.remove("_flag_array")
    for a in expected_required:
        assert a in required, (
            "expected attribute " + a + " not returned in required iterator"
        )

    uv_cal_object.quality_array = 1
    uv_cal_object.flag_array = 1
    required = []
    for prop in uv_cal_object.required():
        required.append(prop)
    for a in required_parameters:
        assert a in required, (
            "expected attribute " + a + " not returned in required iterator"
        )


def test_unexpected_parameters(uvcal_data):
    """Test for extra parameters."""
    (
        uv_cal_object,
        required_parameters,
        required_properties,
        extra_parameters,
        extra_properties,
        other_properties,
    ) = uvcal_data
    expected_parameters = required_parameters + extra_parameters
    attributes = [i for i in uv_cal_object.__dict__.keys() if i[0] == "_"]
    for a in attributes:
        assert a in expected_parameters, "unexpected parameter " + a + " found in UVCal"


def test_unexpected_attributes(uvcal_data):
    """Test for extra attributes."""
    (
        uv_cal_object,
        required_parameters,
        required_properties,
        extra_parameters,
        extra_properties,
        other_properties,
    ) = uvcal_data
    expected_attributes = required_properties + extra_properties + other_properties
    attributes = [i for i in uv_cal_object.__dict__.keys() if i[0] != "_"]
    for a in attributes:
        assert a in expected_attributes, "unexpected attribute " + a + " found in UVCal"


def test_properties(uvcal_data):
    """Test that properties can be get and set properly."""
    (
        uv_cal_object,
        required_parameters,
        required_properties,
        extra_parameters,
        extra_properties,
        other_properties,
    ) = uvcal_data
    prop_dict = dict(
        list(
            zip(
                required_properties + extra_properties,
                required_parameters + extra_parameters,
            )
        )
    )
    for k, v in prop_dict.items():
        rand_num = np.random.rand()
        setattr(uv_cal_object, k, rand_num)
        this_param = getattr(uv_cal_object, v)
        try:
            assert rand_num == this_param.value
        except AssertionError:
            print("setting {prop_name} to a random number failed".format(prop_name=k))
            raise


def test_equality(gain_data):
    """Basic equality test"""
    assert gain_data == gain_data


def test_check(gain_data):
    """Test that parameter checks run properly"""
    assert gain_data.check()


def test_check_warnings(gain_data):
    """Test that parameter checks run properly"""
    gain_data.telescope_location = None
    gain_data.lst_array = None
    gain_data.antenna_positions = None

    with uvtest.check_warnings(
        DeprecationWarning,
        [
            "The telescope_location is not set. It will be a required "
            "parameter starting in pyuvdata version 2.3",
            "The antenna_positions parameter is not set. It will be a required "
            "parameter starting in pyuvdata version 2.3",
            "The lst_array is not set. It will be a required "
            "parameter starting in pyuvdata version 2.3",
        ],
    ):
        assert gain_data.check()


def test_check_flag_array(gain_data):
    gain_data.flag_array = np.ones((gain_data.flag_array.shape), dtype=int)

    with pytest.raises(
        ValueError, match="UVParameter _flag_array is not the appropriate type.",
    ):
        gain_data.check()


@pytest.mark.parametrize("caltype", ["gain", "delay"])
def test_future_array_shape(caltype, gain_data, delay_data_inputflag):
    """Convert to future shapes and check. Convert back and test for equality."""
    if caltype == "gain":
        calobj = gain_data
        calobj.total_quality_array = np.ones(
            (calobj._total_quality_array.expected_shape(calobj))
        )
        calobj.input_flag_array = np.zeros(
            calobj._input_flag_array.expected_shape(calobj)
        ).astype(np.bool_)
    else:
        calobj = delay_data_inputflag
        calobj.total_quality_array = np.ones(
            (calobj._total_quality_array.expected_shape(calobj))
        )
        calobj.input_flag_array = np.zeros(
            calobj._input_flag_array.expected_shape(calobj)
        ).astype(np.bool_)

    calobj2 = calobj.copy()

    calobj.use_future_array_shapes()
    calobj.check()

    calobj.use_current_array_shapes()
    calobj.check()

    assert calobj == calobj2


@pytest.mark.parametrize("caltype", ["gain", "delay"])
def test_future_array_shape_errors(caltype, gain_data, delay_data_inputflag):
    if caltype == "gain":
        calobj = gain_data
        calobj2 = calobj.copy()
    else:
        calobj = delay_data_inputflag

    calobj.use_future_array_shapes()
    calobj.integration_time[-1] = calobj.integration_time[0] * 2.0
    calobj.check()

    with pytest.raises(
        ValueError, match="integration_time parameter contains multiple unique values"
    ):
        calobj.use_current_array_shapes()

    with pytest.raises(
        ValueError, match="The integration times are variable. The calfits format"
    ):
        calobj.write_calfits("foo")

    if caltype == "gain":
        calobj2.use_future_array_shapes()
        calobj2.channel_width[-1] = calobj2.channel_width[0] * 2.0
        calobj2.check()

        with pytest.raises(
            ValueError, match="channel_width parameter contains multiple unique values"
        ):
            calobj2.use_current_array_shapes()

        with pytest.raises(ValueError, match="The frequencies are not evenly spaced"):
            calobj2._check_freq_spacing()


def test_unknown_telescopes(gain_data, tmp_path):
    calobj = gain_data
    calobj.telescope_name = "foo"
    calobj.telescope_location = None
    calobj.lst_array = None
    calobj.antenna_positions = None

    write_file_calfits = str(tmp_path / "test.calfits")
    deprecation_messages = [
        "The telescope_location is not set. It will be a required "
        "parameter starting in pyuvdata version 2.3",
        "The antenna_positions parameter is not set. It will be a required "
        "parameter starting in pyuvdata version 2.3",
        "The lst_array is not set. It will be a required "
        "parameter starting in pyuvdata version 2.3",
    ]

    with uvtest.check_warnings(DeprecationWarning, match=deprecation_messages):
        calobj.write_calfits(write_file_calfits, clobber=True)

    calobj2 = UVCal()
    with uvtest.check_warnings(
        [UserWarning] + [DeprecationWarning] * 3,
        match=["Telescope foo is not in known_telescopes"] + deprecation_messages,
    ):
        calobj2.read_calfits(write_file_calfits)


def test_nants_data_telescope_larger(gain_data):
    # make sure it's okay for Nants_telescope to be strictly greater than Nants_data
    gain_data.Nants_telescope += 1
    # add dummy information for "new antenna" to pass object check
    gain_data.antenna_names = np.concatenate((gain_data.antenna_names, ["dummy_ant"]))
    gain_data.antenna_numbers = np.concatenate((gain_data.antenna_numbers, [20]))
    gain_data.antenna_positions = np.concatenate(
        (gain_data.antenna_positions, np.zeros((1, 3), dtype=float))
    )
    assert gain_data.check()


def test_ant_array_not_in_antnums(gain_data):
    # make sure an error is raised if antennas with data not in antenna_numbers
    # remove antennas from antenna_names & antenna_numbers by hand
    gain_data.antenna_names = gain_data.antenna_names[1:]
    gain_data.antenna_numbers = gain_data.antenna_numbers[1:]
    gain_data.antenna_positions = gain_data.antenna_positions[1:, :]
    gain_data.Nants_telescope = gain_data.antenna_numbers.size
    with pytest.raises(ValueError) as cm:
        gain_data.check()
    assert str(cm.value).startswith(
        "All antennas in ant_array must be in antenna_numbers"
    )


def test_set_gain(gain_data, delay_data):
    delay_data._set_gain()
    assert delay_data._gain_array.required
    assert not delay_data._delay_array.required
    assert delay_data._gain_array.form == delay_data._flag_array.form
    assert delay_data._gain_array.form == delay_data._quality_array.form


def test_set_delay(gain_data):
    gain_data._set_delay()
    assert gain_data._delay_array.required
    assert not gain_data._gain_array.required
    assert gain_data._gain_array.form == gain_data._flag_array.form
    assert gain_data._delay_array.form == gain_data._quality_array.form


def test_set_unknown(gain_data):
    gain_data._set_unknown_cal_type()
    assert not gain_data._delay_array.required
    assert not gain_data._gain_array.required
    assert gain_data._gain_array.form == gain_data._flag_array.form
    assert gain_data._gain_array.form == gain_data._quality_array.form


def test_set_sky(gain_data):
    gain_data._set_sky()
    assert gain_data._sky_field.required
    assert gain_data._sky_catalog.required
    assert gain_data._ref_antenna_name.required


def test_set_redundant(gain_data):
    gain_data._set_redundant()
    assert not gain_data._sky_field.required
    assert not gain_data._sky_catalog.required
    assert not gain_data._ref_antenna_name.required


def test_convert_filetype(gain_data):
    # error testing
    with pytest.raises(ValueError, match="filetype must be calfits."):
        gain_data._convert_to_filetype("uvfits")


def test_error_metadata_only_write(gain_data, tmp_path):
    calobj = gain_data.copy(metadata_only=True)

    out_file = os.path.join(tmp_path, "outtest.calfits")
    with pytest.raises(ValueError, match="Cannot write out metadata only objects to a"):
        calobj.write_calfits(out_file)


def test_flexible_spw(gain_data):
    calobj = gain_data

    # check that this check passes on non-flex_spw objects
    assert calobj._check_flex_spw_contiguous()

    # first just make one spw and check that object still passes check
    calobj._set_flex_spw()
    calobj.channel_width = (
        np.zeros(calobj.Nfreqs, dtype=np.float64) + calobj.channel_width
    )
    calobj.flex_spw_id_array = np.zeros(calobj.Nfreqs, dtype=int)
    calobj.check()

    # now make two
    calobj.Nspws = 2
    calobj.flex_spw_id_array = np.concatenate(
        (
            np.ones(calobj.Nfreqs // 2, dtype=int),
            np.full(calobj.Nfreqs // 2, 2, dtype=int),
        )
    )
    calobj.spw_array = np.array([1, 2])
    calobj.check()

    calobj._check_flex_spw_contiguous()

    # now mix them up
    calobj.Nspws = 2
    calobj.flex_spw_id_array = np.concatenate(
        (
            np.ones(2, dtype=int),
            np.full(2, 2, dtype=int),
            np.ones(2, dtype=int),
            np.full(2, 2, dtype=int),
            np.ones(2, dtype=int),
        )
    )
    calobj.spw_array = np.array([1, 2])
    calobj.check()

    with pytest.raises(
        ValueError, match="Channels from different spectral windows are interspersed",
    ):
        calobj._check_flex_spw_contiguous()


@pytest.mark.parametrize("future_shapes", [True, False])
@pytest.mark.parametrize("convention", ["minus", "plus"])
def test_convert_to_gain(future_shapes, convention, delay_data_inputflag):
    delay_obj = delay_data_inputflag

    if future_shapes:
        delay_obj.use_future_array_shapes()

    new_gain_obj = delay_obj.copy()
    tqa_size = new_gain_obj.delay_array.shape[1:]
    new_gain_obj.total_quality_array = np.ones(tqa_size)

    new_gain_obj.convert_to_gain(delay_convention=convention)
    assert np.isclose(
        np.max(np.absolute(new_gain_obj.gain_array)),
        1.0,
        rtol=new_gain_obj._gain_array.tols[0],
        atol=new_gain_obj._gain_array.tols[1],
    )
    assert np.isclose(
        np.min(np.absolute(new_gain_obj.gain_array)),
        1.0,
        rtol=new_gain_obj._gain_array.tols[0],
        atol=new_gain_obj._gain_array.tols[1],
    )

    if convention == "minus":
        conv = -1
    else:
        conv = 1
    if future_shapes:
        assert np.allclose(
            np.angle(new_gain_obj.gain_array[:, 10, :, :]) % (2 * np.pi),
            (
                conv
                * 2
                * np.pi
                * delay_obj.delay_array[:, 0, :, :]
                * delay_obj.freq_array[10]
            )
            % (2 * np.pi),
            rtol=new_gain_obj._gain_array.tols[0],
            atol=new_gain_obj._gain_array.tols[1],
        )
        assert np.allclose(
            delay_obj.quality_array,
            new_gain_obj.quality_array[:, 10, :, :],
            rtol=new_gain_obj._quality_array.tols[0],
            atol=new_gain_obj._quality_array.tols[1],
        )

    else:
        assert np.allclose(
            np.angle(new_gain_obj.gain_array[:, :, 10, :, :]) % (2 * np.pi),
            (
                conv
                * 2
                * np.pi
                * delay_obj.delay_array[:, :, 0, :, :]
                * delay_obj.freq_array[0, 10]
            )
            % (2 * np.pi),
            rtol=new_gain_obj._gain_array.tols[0],
            atol=new_gain_obj._gain_array.tols[1],
        )
        assert np.allclose(
            delay_obj.quality_array,
            new_gain_obj.quality_array[:, :, 10, :, :],
            rtol=new_gain_obj._quality_array.tols[0],
            atol=new_gain_obj._quality_array.tols[1],
        )

    assert new_gain_obj.history == (
        delay_obj.history + "  Converted from delays to gains using pyuvdata."
    )


def test_convert_to_gain_errors(gain_data, delay_data_inputflag):
    delay_obj = delay_data_inputflag
    gain_obj = gain_data

    with pytest.raises(
        ValueError, match="delay_convention can only be 'minus' or 'plus'",
    ):
        delay_obj.convert_to_gain(delay_convention="bogus")

    with pytest.raises(
        ValueError, match="The data is already a gain cal_type.",
    ):
        gain_obj.convert_to_gain()

    gain_obj._set_unknown_cal_type()
    with pytest.raises(
        ValueError, match="cal_type is unknown, cannot convert to gain",
    ):
        gain_obj.convert_to_gain()


@pytest.mark.parametrize("future_shapes", [True, False])
@pytest.mark.parametrize("caltype", ["gain", "delay"])
def test_select_antennas(
    caltype, future_shapes, gain_data, delay_data_inputflag, tmp_path
):
    if caltype == "gain":
        calobj = gain_data
    else:
        calobj = delay_data_inputflag

    if future_shapes:
        calobj.use_future_array_shapes()

    calobj2 = calobj.copy()

    old_history = calobj.history
    ants_to_keep = np.array([65, 96, 9, 97, 89, 22, 20, 72])
    calobj2.select(antenna_nums=ants_to_keep)

    assert len(ants_to_keep) == calobj2.Nants_data
    for ant in ants_to_keep:
        assert ant in calobj2.ant_array
    for ant in calobj2.ant_array:
        assert ant in ants_to_keep

    assert uvutils._check_histories(
        old_history + "  Downselected to specific antennas using pyuvdata.",
        calobj2.history,
    )

    # now test using antenna_names to specify antennas to keep
    ants_to_keep = np.array(sorted(ants_to_keep))
    ant_names = []
    for a in ants_to_keep:
        ind = np.where(calobj.antenna_numbers == a)[0][0]
        ant_names.append(calobj.antenna_names[ind])

    calobj3 = calobj.select(antenna_names=ant_names, inplace=False)

    assert calobj2 == calobj3

    # check for errors associated with antennas not included in data, bad names
    # or providing numbers and names
    with pytest.raises(
        ValueError,
        match=f"Antenna number {np.max(calobj.ant_array)+1} "
        "is not present in the array",
    ):
        calobj.select(antenna_nums=np.max(calobj.ant_array) + np.arange(1, 3))

    with pytest.raises(
        ValueError, match="Antenna name test1 is not present in the antenna_names array"
    ):
        calobj.select(antenna_names=["test1"])
    with pytest.raises(
        ValueError, match="Only one of antenna_nums and antenna_names can be provided."
    ):
        calobj.select(antenna_nums=ants_to_keep, antenna_names=ant_names)

    # check that write_calfits works with Nants_data < Nants_telescope
    write_file_calfits = str(tmp_path / "select_test.calfits")
    calobj2.write_calfits(write_file_calfits, clobber=True)

    # check that reading it back in works too
    new_gain_object = UVCal()
    new_gain_object.read_calfits(write_file_calfits)
    if future_shapes:
        new_gain_object.use_future_array_shapes()
    assert calobj2 == new_gain_object

    # check that total_quality_array is handled properly when present
    calobj.total_quality_array = np.zeros(
        calobj._total_quality_array.expected_shape(calobj)
    )
    with uvtest.check_warnings(
        UserWarning, match="Cannot preserve total_quality_array",
    ):
        calobj.select(antenna_names=ant_names, inplace=True)
    assert calobj.total_quality_array is None


@pytest.mark.parametrize("future_shapes", [True, False])
@pytest.mark.parametrize("caltype", ["gain", "delay"])
def test_select_times(
    future_shapes, caltype, gain_data, delay_data_inputflag, tmp_path
):
    if caltype == "gain":
        calobj = gain_data
    else:
        calobj = delay_data_inputflag

    if future_shapes:
        calobj.use_future_array_shapes()

    calobj2 = calobj.copy()

    old_history = calobj.history
    times_to_keep = calobj.time_array[2:5]

    calobj2.select(times=times_to_keep)

    assert len(times_to_keep) == calobj2.Ntimes
    for t in times_to_keep:
        assert t in calobj2.time_array
    for t in np.unique(calobj2.time_array):
        assert t in times_to_keep

    assert uvutils._check_histories(
        old_history + "  Downselected to specific times using pyuvdata.",
        calobj2.history,
    )

    write_file_calfits = str(tmp_path / "select_test.calfits")
    # test writing calfits with only one time
    calobj2 = calobj.copy()
    times_to_keep = calobj.time_array[[1]]
    calobj2.select(times=times_to_keep)
    calobj2.write_calfits(write_file_calfits, clobber=True)

    # check for errors associated with times not included in data
    pytest.raises(
        ValueError,
        calobj.select,
        times=[np.min(calobj.time_array) - calobj.integration_time],
    )

    # check for warnings and errors associated with unevenly spaced times
    calobj2 = calobj.copy()
    with uvtest.check_warnings(
        UserWarning, match="Selected times are not evenly spaced",
    ):
        calobj2.select(times=calobj2.time_array[[0, 2, 3]])
    pytest.raises(ValueError, calobj2.write_calfits, write_file_calfits)


@pytest.mark.parametrize("future_shapes", [True, False])
@pytest.mark.parametrize("caltype", ["gain", "delay"])
def test_select_frequencies(
    future_shapes, caltype, gain_data, delay_data_inputflag, tmp_path
):
    if caltype == "gain":
        calobj = gain_data
    else:
        calobj = delay_data_inputflag

    if future_shapes:
        calobj.use_future_array_shapes()

    calobj2 = calobj.copy()

    old_history = calobj.history

    if future_shapes:
        freqs_to_keep = calobj.freq_array[np.arange(4, 8)]
    else:
        freqs_to_keep = calobj.freq_array[0, np.arange(4, 8)]

    # add dummy total_quality_array
    calobj.total_quality_array = np.zeros(
        calobj._total_quality_array.expected_shape(calobj)
    )
    calobj2.total_quality_array = np.zeros(
        calobj2._total_quality_array.expected_shape(calobj2)
    )

    calobj2.select(frequencies=freqs_to_keep)

    assert len(freqs_to_keep) == calobj2.Nfreqs
    for f in freqs_to_keep:
        assert f in calobj2.freq_array
    for f in np.unique(calobj2.freq_array):
        assert f in freqs_to_keep

    assert uvutils._check_histories(
        old_history + "  Downselected to specific frequencies using pyuvdata.",
        calobj2.history,
    )

    write_file_calfits = str(tmp_path / "select_test.calfits")
    # test writing calfits with only one frequency
    calobj2 = calobj.copy()
    if future_shapes:
        freqs_to_keep = calobj.freq_array[5]
    else:
        freqs_to_keep = calobj.freq_array[0, 5]
    calobj2.select(frequencies=freqs_to_keep)
    calobj2.write_calfits(write_file_calfits, clobber=True)

    # test writing calfits with frequencies spaced by more than the channel width
    calobj2 = calobj.copy()
    if future_shapes:
        freqs_to_keep = calobj.freq_array[[0, 2, 4, 6, 8]]
    else:
        freqs_to_keep = calobj.freq_array[0, [0, 2, 4, 6, 8]]
    with uvtest.check_warnings(
        UserWarning, match="Selected frequencies are not contiguous."
    ):
        calobj2.select(frequencies=freqs_to_keep)
    calobj2.write_calfits(write_file_calfits, clobber=True)

    # check for errors associated with frequencies not included in data
    pytest.raises(
        ValueError,
        calobj.select,
        frequencies=[np.max(calobj.freq_array) + calobj.channel_width],
    )

    # check for warnings and errors associated with unevenly spaced frequencies
    calobj2 = calobj.copy()
    if future_shapes:
        freqs_to_keep = calobj2.freq_array[[0, 5, 6]]
    else:
        freqs_to_keep = calobj2.freq_array[0, [0, 5, 6]]
    with uvtest.check_warnings(
        UserWarning, match="Selected frequencies are not evenly spaced",
    ):
        calobj2.select(frequencies=freqs_to_keep)

    with pytest.raises(
        ValueError,
        match="Frequencies are not evenly spaced or have differing values of channel",
    ):
        calobj2.write_calfits(write_file_calfits)


@pytest.mark.parametrize("future_shapes", [True, False])
def test_select_frequencies_multispw(future_shapes, multi_spw_gain, tmp_path):
    calobj = multi_spw_gain

    if future_shapes:
        calobj.use_future_array_shapes()

    calobj2 = calobj.copy()
    old_history = calobj.history

    if future_shapes:
        freqs_to_keep = calobj.freq_array[np.arange(4, 8)]
    else:
        freqs_to_keep = calobj.freq_array[0, np.arange(4, 8)]

    # add dummy total_quality_array
    calobj.total_quality_array = np.zeros(
        calobj._total_quality_array.expected_shape(calobj)
    )
    calobj2.total_quality_array = np.zeros(
        calobj2._total_quality_array.expected_shape(calobj2)
    )

    # add dummy input_flag_array
    calobj.input_flag_array = np.zeros(
        calobj._input_flag_array.expected_shape(calobj)
    ).astype(np.bool_)
    calobj2.input_flag_array = np.zeros(
        calobj2._input_flag_array.expected_shape(calobj2)
    ).astype(np.bool_)

    calobj2.select(frequencies=freqs_to_keep)

    assert len(freqs_to_keep) == calobj2.Nfreqs
    for f in freqs_to_keep:
        assert f in calobj2.freq_array
    for f in np.unique(calobj2.freq_array):
        assert f in freqs_to_keep

    assert uvutils._check_histories(
        old_history + "  Downselected to specific frequencies using pyuvdata.",
        calobj2.history,
    )

    # test calfits write error
    write_file_calfits = str(tmp_path / "select_test.calfits")
    with pytest.raises(
        ValueError,
        match="The calfits format does not support multiple spectral windows",
    ):
        calobj2.write_calfits(write_file_calfits, clobber=True)

    # test that we can write to calfits if select to only one spw
    calobj2 = calobj.copy()

    if future_shapes:
        freqs_to_keep = calobj.freq_array[np.arange(3)]
    else:
        freqs_to_keep = calobj.freq_array[0, np.arange(3)]

    calobj2.select(frequencies=freqs_to_keep)
    calobj2.check()

    assert len(freqs_to_keep) == calobj2.Nfreqs
    for f in freqs_to_keep:
        assert f in calobj2.freq_array
    for f in np.unique(calobj2.freq_array):
        assert f in freqs_to_keep

    assert calobj2.Nspws == 1
    calobj2.write_calfits(write_file_calfits, clobber=True)

    calobj3 = UVCal()
    calobj3.read_calfits(write_file_calfits)
    if future_shapes:
        calobj3.use_future_array_shapes()

    calobj2.flex_spw = False
    calobj2._flex_spw_id_array.required = False
    calobj2.flex_spw_id_array = None
    calobj2.spw_array = np.array([0])
    if not future_shapes:
        calobj2._channel_width.form = ()
        calobj2.channel_width = calobj2.channel_width[0]
    calobj2.check()

    assert calobj3 == calobj2


@pytest.mark.parametrize("caltype", ["gain", "delay"])
def test_select_freq_chans(caltype, gain_data, delay_data_inputflag):
    if caltype == "gain":
        calobj = gain_data
    else:
        calobj = delay_data_inputflag

    calobj2 = calobj.copy()

    old_history = calobj.history
    chans_to_keep = np.arange(4, 8)

    # add dummy total_quality_array
    calobj.total_quality_array = np.zeros(
        calobj._total_quality_array.expected_shape(calobj)
    )
    calobj2.total_quality_array = np.zeros(
        calobj2._total_quality_array.expected_shape(calobj2)
    )

    calobj2.select(freq_chans=chans_to_keep)

    assert len(chans_to_keep) == calobj2.Nfreqs
    for chan in chans_to_keep:
        assert calobj.freq_array[0, chan] in calobj2.freq_array
    for f in np.unique(calobj2.freq_array):
        assert f in calobj.freq_array[0, chans_to_keep]

    assert uvutils._check_histories(
        old_history + "  Downselected to specific frequencies using pyuvdata.",
        calobj2.history,
    )

    # Test selecting both channels and frequencies
    freqs_to_keep = calobj.freq_array[0, np.arange(7, 10)]  # Overlaps with chans
    all_chans_to_keep = np.arange(4, 10)

    calobj2 = calobj.copy()
    calobj2.select(frequencies=freqs_to_keep, freq_chans=chans_to_keep)

    assert len(all_chans_to_keep) == calobj2.Nfreqs
    for chan in all_chans_to_keep:
        assert calobj.freq_array[0, chan] in calobj2.freq_array
    for f in np.unique(calobj2.freq_array):
        assert f in calobj.freq_array[0, all_chans_to_keep]


@pytest.mark.parametrize("future_shapes", [True, False])
@pytest.mark.parametrize("caltype", ["gain", "delay"])
@pytest.mark.parametrize(
    "jones_to_keep", ([-5, -6], ["xx", "yy"], ["nn", "ee"], [[-5, -6]])
)
def test_select_polarizations(
    future_shapes, caltype, jones_to_keep, gain_data, delay_data_inputflag, tmp_path
):
    if caltype == "gain":
        calobj = gain_data
    else:
        calobj = delay_data_inputflag

    if future_shapes:
        calobj.use_future_array_shapes()

    calobj2 = calobj.copy()

    # add more jones terms to allow for better testing of selections
    while calobj.Njones < 4:
        new_jones = np.min(calobj.jones_array) - 1
        calobj.jones_array = np.append(calobj.jones_array, new_jones)
        calobj.Njones += 1
        if future_shapes:
            calobj.flag_array = np.concatenate(
                (calobj.flag_array, calobj.flag_array[:, :, :, [-1]],), axis=3,
            )
            if calobj.input_flag_array is not None:
                calobj.input_flag_array = np.concatenate(
                    (calobj.input_flag_array, calobj.input_flag_array[:, :, :, [-1]],),
                    axis=3,
                )
            if caltype == "gain":
                calobj.gain_array = np.concatenate(
                    (calobj.gain_array, calobj.gain_array[:, :, :, [-1]],), axis=3,
                )
            else:
                calobj.delay_array = np.concatenate(
                    (calobj.delay_array, calobj.delay_array[:, :, :, [-1]],), axis=3,
                )
            calobj.quality_array = np.concatenate(
                (calobj.quality_array, calobj.quality_array[:, :, :, [-1]],), axis=3,
            )
        else:
            calobj.flag_array = np.concatenate(
                (calobj.flag_array, calobj.flag_array[:, :, :, :, [-1]],), axis=4,
            )
            if calobj.input_flag_array is not None:
                calobj.input_flag_array = np.concatenate(
                    (
                        calobj.input_flag_array,
                        calobj.input_flag_array[:, :, :, :, [-1]],
                    ),
                    axis=4,
                )
            if caltype == "gain":
                calobj.gain_array = np.concatenate(
                    (calobj.gain_array, calobj.gain_array[:, :, :, :, [-1]],), axis=4,
                )
            else:
                calobj.delay_array = np.concatenate(
                    (calobj.delay_array, calobj.delay_array[:, :, :, :, [-1]],), axis=4,
                )
            calobj.quality_array = np.concatenate(
                (calobj.quality_array, calobj.quality_array[:, :, :, :, [-1]],), axis=4,
            )
    # add dummy total_quality_array
    calobj.total_quality_array = np.zeros(
        calobj._total_quality_array.expected_shape(calobj)
    )

    assert calobj.check()
    calobj2 = calobj.copy()

    old_history = calobj.history

    calobj2.select(jones=jones_to_keep)

    if isinstance(jones_to_keep[0], list):
        jones_to_keep = jones_to_keep[0]
    assert len(jones_to_keep) == calobj2.Njones
    for j in jones_to_keep:
        if isinstance(j, int):
            assert j in calobj2.jones_array
        else:
            assert (
                uvutils.jstr2num(j, x_orientation=calobj2.x_orientation)
                in calobj2.jones_array
            )
    for j in np.unique(calobj2.jones_array):
        if isinstance(jones_to_keep[0], int):
            assert j in jones_to_keep
        else:
            assert j in uvutils.jstr2num(
                jones_to_keep, x_orientation=calobj2.x_orientation
            )

    assert uvutils._check_histories(
        old_history + "  Downselected to "
        "specific jones polarization terms "
        "using pyuvdata.",
        calobj2.history,
    )

    # check for errors associated with polarizations not included in data
    pytest.raises(ValueError, calobj2.select, jones=[-3, -4])

    # check for warnings and errors associated with unevenly spaced polarizations
    with uvtest.check_warnings(
        UserWarning, match="Selected jones polarization terms are not evenly spaced",
    ):
        calobj.select(jones=calobj.jones_array[[0, 1, 3]])
    write_file_calfits = os.path.join(tmp_path, "select_test.calfits")
    pytest.raises(ValueError, calobj.write_calfits, write_file_calfits)


@pytest.mark.parametrize("future_shapes", [True, False])
@pytest.mark.parametrize("caltype", ["gain", "delay"])
def test_select(future_shapes, caltype, gain_data, delay_data_inputflag):
    # now test selecting along all axes at once
    if caltype == "gain":
        calobj = gain_data
    else:
        calobj = delay_data_inputflag

    if future_shapes:
        calobj.use_future_array_shapes()

    calobj2 = calobj.copy()

    old_history = calobj.history

    ants_to_keep = np.array([10, 89, 43, 9, 80, 96, 64])
    if future_shapes:
        freqs_to_keep = calobj.freq_array[np.arange(2, 5)]
    else:
        freqs_to_keep = calobj.freq_array[0, np.arange(2, 5)]
    times_to_keep = calobj.time_array[[1, 2]]
    jones_to_keep = [-5]

    calobj2.select(
        antenna_nums=ants_to_keep,
        frequencies=freqs_to_keep,
        times=times_to_keep,
        jones=jones_to_keep,
    )

    assert len(ants_to_keep) == calobj2.Nants_data
    for ant in ants_to_keep:
        assert ant in calobj2.ant_array
    for ant in calobj2.ant_array:
        assert ant in ants_to_keep

    assert len(times_to_keep) == calobj2.Ntimes
    for t in times_to_keep:
        assert t in calobj2.time_array
    for t in np.unique(calobj2.time_array):
        assert t in times_to_keep

    assert len(freqs_to_keep) == calobj2.Nfreqs
    for f in freqs_to_keep:
        assert f in calobj2.freq_array
    for f in np.unique(calobj2.freq_array):
        assert f in freqs_to_keep

    assert len(jones_to_keep) == calobj2.Njones
    for j in jones_to_keep:
        assert j in calobj2.jones_array
    for j in np.unique(calobj2.jones_array):
        assert j in jones_to_keep

    assert uvutils._check_histories(
        old_history + "  Downselected to "
        "specific antennas, times, "
        "frequencies, jones polarization terms "
        "using pyuvdata.",
        calobj2.history,
    )


@pytest.mark.parametrize("future_shapes", [True, False])
@pytest.mark.parametrize("caltype", ["gain", "delay"])
def test_add_antennas(future_shapes, caltype, gain_data, delay_data_inputflag):
    """Test adding antennas between two UVCal objects"""
    if caltype == "gain":
        calobj = gain_data
    else:
        calobj = delay_data_inputflag

    if future_shapes:
        calobj.use_future_array_shapes()

    calobj2 = calobj.copy()

    calobj_full = calobj.copy()
    ants1 = np.array([9, 10, 20, 22, 31, 43, 53, 64, 65, 72])
    ants2 = np.array([80, 81, 88, 89, 96, 97, 104, 105, 112])
    calobj.select(antenna_nums=ants1)
    calobj2.select(antenna_nums=ants2)
    calobj += calobj2
    # Check history is correct, before replacing and doing a full object check
    assert uvutils._check_histories(
        calobj_full.history + "  Downselected to specific "
        "antennas using pyuvdata. Combined "
        "data along antenna axis using pyuvdata.",
        calobj.history,
    )
    calobj.history = calobj_full.history
    assert calobj == calobj_full

    # test for when total_quality_array is present
    calobj.select(antenna_nums=ants1)
    calobj.total_quality_array = np.zeros(
        calobj._total_quality_array.expected_shape(calobj)
    )
    with uvtest.check_warnings(UserWarning, match="Total quality array detected"):
        calobj.__iadd__(calobj2)
    assert calobj.total_quality_array is None

    if caltype == "delay":
        # test for when input_flag_array is present in first file but not second
        calobj.select(antenna_nums=ants1)
        ifa = np.zeros(calobj._input_flag_array.expected_shape(calobj)).astype(np.bool_)
        ifa2 = np.ones(calobj2._input_flag_array.expected_shape(calobj2)).astype(
            np.bool_
        )
        tot_ifa = np.concatenate([ifa, ifa2], axis=0)
        calobj.input_flag_array = ifa
        calobj2.input_flag_array = None
        calobj += calobj2
        assert np.allclose(calobj.input_flag_array, tot_ifa)

        # test for when input_flag_array is present in second file but not first
        calobj.select(antenna_nums=ants1)
        ifa = np.ones(calobj._input_flag_array.expected_shape(calobj)).astype(np.bool_)
        ifa2 = np.zeros(calobj2._input_flag_array.expected_shape(calobj2)).astype(
            np.bool_
        )
        tot_ifa = np.concatenate([ifa, ifa2], axis=0)
        calobj.input_flag_array = None
        calobj2.input_flag_array = ifa2
        calobj += calobj2
        assert np.allclose(calobj.input_flag_array, tot_ifa)

    # Out of order - antennas
    calobj = calobj_full.copy()
    calobj2 = calobj.copy()
    calobj.select(antenna_nums=ants2)
    calobj2.select(antenna_nums=ants1)
    calobj += calobj2
    calobj.history = calobj_full.history
    assert calobj == calobj_full


@pytest.mark.parametrize("future_shapes", [True, False])
def test_add_antennas_multispw(future_shapes, multi_spw_gain):
    """Test adding antennas between two UVCal objects"""
    calobj = multi_spw_gain

    if future_shapes:
        calobj.use_future_array_shapes()

    calobj2 = calobj.copy()

    calobj_full = calobj.copy()
    ants1 = np.array([9, 10, 20, 22, 31, 43, 53, 64, 65, 72])
    ants2 = np.array([80, 81, 88, 89, 96, 97, 104, 105, 112])
    calobj.select(antenna_nums=ants1)
    calobj2.select(antenna_nums=ants2)
    calobj += calobj2
    # Check history is correct, before replacing and doing a full object check
    assert uvutils._check_histories(
        calobj_full.history + "  Downselected to specific "
        "antennas using pyuvdata. Combined "
        "data along antenna axis using pyuvdata.",
        calobj.history,
    )
    calobj.history = calobj_full.history
    assert calobj == calobj_full


@pytest.mark.parametrize("future_shapes", [True, False])
def test_add_frequencies(future_shapes, gain_data):
    """Test adding frequencies between two UVCal objects"""
    # don't test on delays because there's no freq axis for the delay array
    calobj = gain_data

    if future_shapes:
        calobj.use_future_array_shapes()

    calobj2 = calobj.copy()

    calobj_full = calobj.copy()
    if future_shapes:
        freqs1 = calobj.freq_array[np.arange(0, calobj.Nfreqs // 2)]
        freqs2 = calobj.freq_array[np.arange(calobj.Nfreqs // 2, calobj.Nfreqs)]
    else:
        freqs1 = calobj.freq_array[0, np.arange(0, calobj.Nfreqs // 2)]
        freqs2 = calobj.freq_array[0, np.arange(calobj.Nfreqs // 2, calobj.Nfreqs)]
    calobj.select(frequencies=freqs1)
    calobj2.select(frequencies=freqs2)
    calobj += calobj2
    # Check history is correct, before replacing and doing a full object check
    assert uvutils._check_histories(
        calobj_full.history + "  Downselected to specific "
        "frequencies using pyuvdata. Combined "
        "data along frequency axis using pyuvdata.",
        calobj.history,
    )
    calobj.history = calobj_full.history
    assert calobj == calobj_full

    # test for when total_quality_array is present in first file but not second
    calobj.select(frequencies=freqs1)
    tqa = np.ones(calobj._total_quality_array.expected_shape(calobj))
    tqa2 = np.zeros(calobj2._total_quality_array.expected_shape(calobj2))
    if future_shapes:
        tot_tqa = np.concatenate([tqa, tqa2], axis=0)
    else:
        tot_tqa = np.concatenate([tqa, tqa2], axis=1)
    calobj.total_quality_array = tqa
    calobj += calobj2
    assert np.allclose(
        calobj.total_quality_array,
        tot_tqa,
        rtol=calobj._total_quality_array.tols[0],
        atol=calobj._total_quality_array.tols[1],
    )

    # test for when total_quality_array is present in second file but not first
    calobj.select(frequencies=freqs1)
    tqa = np.zeros(calobj._total_quality_array.expected_shape(calobj))
    tqa2 = np.ones(calobj2._total_quality_array.expected_shape(calobj2))
    if future_shapes:
        tot_tqa = np.concatenate([tqa, tqa2], axis=0)
    else:
        tot_tqa = np.concatenate([tqa, tqa2], axis=1)
    calobj.total_quality_array = None
    calobj2.total_quality_array = tqa2
    calobj += calobj2
    assert np.allclose(
        calobj.total_quality_array,
        tot_tqa,
        rtol=calobj._total_quality_array.tols[0],
        atol=calobj._total_quality_array.tols[1],
    )

    # test for when total_quality_array is present in both
    calobj.select(frequencies=freqs1)
    tqa = np.ones(calobj._total_quality_array.expected_shape(calobj))
    tqa2 = np.ones(calobj2._total_quality_array.expected_shape(calobj2))
    tqa *= 2
    if future_shapes:
        tot_tqa = np.concatenate([tqa, tqa2], axis=0)
    else:
        tot_tqa = np.concatenate([tqa, tqa2], axis=1)
    calobj.total_quality_array = tqa
    calobj2.total_quality_array = tqa2
    calobj += calobj2
    assert np.allclose(
        calobj.total_quality_array,
        tot_tqa,
        rtol=calobj._total_quality_array.tols[0],
        atol=calobj._total_quality_array.tols[1],
    )

    # test for when input_flag_array is present in first file but not second
    calobj = calobj_full.copy()
    calobj.input_flag_array = np.zeros(
        calobj._input_flag_array.expected_shape(calobj), dtype=bool
    )
    calobj2 = calobj.copy()
    calobj.select(frequencies=freqs1)
    calobj2.select(frequencies=freqs2)
    ifa = np.zeros(calobj._input_flag_array.expected_shape(calobj)).astype(np.bool_)
    ifa2 = np.ones(calobj2._input_flag_array.expected_shape(calobj2)).astype(np.bool_)
    if future_shapes:
        tot_ifa = np.concatenate([ifa, ifa2], axis=1)
    else:
        tot_ifa = np.concatenate([ifa, ifa2], axis=2)
    calobj.input_flag_array = ifa
    calobj2.input_flag_array = None
    calobj += calobj2
    assert np.allclose(calobj.input_flag_array, tot_ifa)

    # test for when input_flag_array is present in second file but not first
    calobj.select(frequencies=freqs1)
    ifa = np.ones(calobj._input_flag_array.expected_shape(calobj)).astype(np.bool_)
    ifa2 = np.zeros(calobj2._input_flag_array.expected_shape(calobj2)).astype(np.bool_)
    if future_shapes:
        tot_ifa = np.concatenate([ifa, ifa2], axis=1)
    else:
        tot_ifa = np.concatenate([ifa, ifa2], axis=2)
    calobj.input_flag_array = None
    calobj2.input_flag_array = ifa2
    calobj += calobj2
    assert np.allclose(calobj.input_flag_array, tot_ifa)

    # Out of order - freqs
    calobj = calobj_full.copy()
    calobj2 = calobj_full.copy()
    calobj.select(frequencies=freqs2)
    calobj2.select(frequencies=freqs1)
    calobj += calobj2
    calobj.history = calobj_full.history
    assert calobj == calobj_full


@pytest.mark.parametrize("future_shapes", [True, False])
@pytest.mark.parametrize("split_f_ind", [3, 5])
def test_add_frequencies_multispw(future_shapes, split_f_ind, multi_spw_gain):
    """Test adding frequencies between two UVCal objects"""
    # don't test on delays because there's no freq axis for the delay array

    # split_f_ind=5 splits the objects in the same place as the spws split
    # (so each object has only one spw). A different value splits within an spw.

    calobj = multi_spw_gain

    if future_shapes:
        calobj.use_future_array_shapes()

    calobj2 = calobj.copy()

    calobj_full = calobj.copy()
    if future_shapes:
        freqs1 = calobj.freq_array[np.arange(0, split_f_ind)]
        freqs2 = calobj.freq_array[np.arange(split_f_ind, calobj.Nfreqs)]
    else:
        freqs1 = calobj.freq_array[0, np.arange(0, split_f_ind)]
        freqs2 = calobj.freq_array[0, np.arange(split_f_ind, calobj.Nfreqs)]
    calobj.select(frequencies=freqs1)
    calobj2.select(frequencies=freqs2)
    calobj += calobj2

    # Check history is correct, before replacing and doing a full object check
    assert uvutils._check_histories(
        calobj_full.history + "  Downselected to specific "
        "frequencies using pyuvdata. Combined "
        "data along frequency axis using pyuvdata.",
        calobj.history,
    )
    calobj.history = calobj_full.history
    assert calobj == calobj_full

    # test adding out of order
    calobj = calobj_full.copy()
    calobj.select(frequencies=freqs1)
    calobj2 += calobj

    # Check history is correct, before replacing and doing a full object check
    assert uvutils._check_histories(
        calobj_full.history + "  Downselected to specific "
        "frequencies using pyuvdata. Combined "
        "data along frequency axis using pyuvdata.",
        calobj2.history,
    )
    calobj2.history = calobj_full.history
    assert calobj2 == calobj_full


@pytest.mark.parametrize("future_shapes", [True, False])
@pytest.mark.parametrize("caltype", ["gain", "delay"])
def test_add_times(future_shapes, caltype, gain_data, delay_data_inputflag):
    """Test adding times between two UVCal objects"""
    if caltype == "gain":
        calobj = gain_data
    else:
        calobj = delay_data_inputflag

    if future_shapes:
        calobj.use_future_array_shapes()

    calobj2 = calobj.copy()

    calobj_full = calobj.copy()
    n_times2 = calobj.Ntimes // 2
    times1 = calobj.time_array[:n_times2]
    times2 = calobj.time_array[n_times2:]
    calobj.select(times=times1)
    calobj2.select(times=times2)
    calobj += calobj2
    # Check history is correct, before replacing and doing a full object check
    assert uvutils._check_histories(
        calobj_full.history + "  Downselected to specific "
        "times using pyuvdata. Combined "
        "data along time axis using pyuvdata.",
        calobj.history,
    )
    calobj.history = calobj_full.history
    assert calobj == calobj_full

    # test for when total_quality_array is present in first file but not second
    calobj.select(times=times1)
    tqa = np.ones(calobj._total_quality_array.expected_shape(calobj))
    tqa2 = np.zeros(calobj2._total_quality_array.expected_shape(calobj2))
    if future_shapes:
        tot_tqa = np.concatenate([tqa, tqa2], axis=1)
    else:
        tot_tqa = np.concatenate([tqa, tqa2], axis=2)
    calobj.total_quality_array = tqa
    calobj += calobj2
    assert np.allclose(
        calobj.total_quality_array,
        tot_tqa,
        rtol=calobj._total_quality_array.tols[0],
        atol=calobj._total_quality_array.tols[1],
    )

    # test for when total_quality_array is present in second file but not first
    calobj.select(times=times1)
    tqa = np.zeros(calobj._total_quality_array.expected_shape(calobj))
    tqa2 = np.ones(calobj2._total_quality_array.expected_shape(calobj2))
    if future_shapes:
        tot_tqa = np.concatenate([tqa, tqa2], axis=1)
    else:
        tot_tqa = np.concatenate([tqa, tqa2], axis=2)
    calobj.total_quality_array = None
    calobj2.total_quality_array = tqa2
    calobj += calobj2
    assert np.allclose(
        calobj.total_quality_array,
        tot_tqa,
        rtol=calobj._total_quality_array.tols[0],
        atol=calobj._total_quality_array.tols[1],
    )

    # test for when total_quality_array is present in both
    calobj.select(times=times1)
    tqa = np.ones(calobj._total_quality_array.expected_shape(calobj))
    tqa2 = np.ones(calobj2._total_quality_array.expected_shape(calobj2))
    tqa *= 2
    if future_shapes:
        tot_tqa = np.concatenate([tqa, tqa2], axis=1)
    else:
        tot_tqa = np.concatenate([tqa, tqa2], axis=2)
    calobj.total_quality_array = tqa
    calobj2.total_quality_array = tqa2
    calobj += calobj2
    assert np.allclose(
        calobj.total_quality_array,
        tot_tqa,
        rtol=calobj._total_quality_array.tols[0],
        atol=calobj._total_quality_array.tols[1],
    )

    if caltype == "delay":
        # test for when input_flag_array is present in first file but not second
        calobj.select(times=times1)
        ifa = np.zeros(calobj._input_flag_array.expected_shape(calobj)).astype(np.bool_)
        ifa2 = np.ones(calobj2._input_flag_array.expected_shape(calobj2)).astype(
            np.bool_
        )
        if future_shapes:
            tot_ifa = np.concatenate([ifa, ifa2], axis=2)
        else:
            tot_ifa = np.concatenate([ifa, ifa2], axis=3)
        calobj.input_flag_array = ifa
        calobj2.input_flag_array = None
        calobj += calobj2
        assert np.allclose(calobj.input_flag_array, tot_ifa)

        # test for when input_flag_array is present in second file but not first
        calobj.select(times=times1)
        ifa = np.ones(calobj._input_flag_array.expected_shape(calobj)).astype(np.bool_)
        ifa2 = np.zeros(calobj2._input_flag_array.expected_shape(calobj2)).astype(
            np.bool_
        )
        if future_shapes:
            tot_ifa = np.concatenate([ifa, ifa2], axis=2)
        else:
            tot_ifa = np.concatenate([ifa, ifa2], axis=3)
        calobj.input_flag_array = None
        calobj2.input_flag_array = ifa2
        calobj += calobj2
        assert np.allclose(calobj.input_flag_array, tot_ifa)

    # Out of order - times
    calobj = calobj_full.copy()
    calobj2 = calobj.copy()
    calobj.select(times=times2)
    calobj2.select(times=times1)
    calobj += calobj2
    calobj.history = calobj_full.history
    assert calobj == calobj_full


@pytest.mark.parametrize("future_shapes", [True, False])
def test_add_times_multispw(future_shapes, multi_spw_gain):
    """Test adding times between two UVCal objects"""
    calobj = multi_spw_gain

    if future_shapes:
        calobj.use_future_array_shapes()

    calobj2 = calobj.copy()

    calobj_full = calobj.copy()
    n_times2 = calobj.Ntimes // 2
    times1 = calobj.time_array[:n_times2]
    times2 = calobj.time_array[n_times2:]
    calobj.select(times=times1)
    calobj2.select(times=times2)
    calobj += calobj2
    # Check history is correct, before replacing and doing a full object check
    assert uvutils._check_histories(
        calobj_full.history + "  Downselected to specific "
        "times using pyuvdata. Combined "
        "data along time axis using pyuvdata.",
        calobj.history,
    )
    calobj.history = calobj_full.history
    assert calobj == calobj_full


@pytest.mark.parametrize("future_shapes", [True, False])
@pytest.mark.parametrize("caltype", ["gain", "delay"])
def test_add_jones(future_shapes, caltype, gain_data, delay_data_inputflag):
    """Test adding Jones axes between two UVCal objects"""
    if caltype == "gain":
        calobj = gain_data
    else:
        calobj = delay_data_inputflag

    if future_shapes:
        calobj.use_future_array_shapes()

    calobj2 = calobj.copy()

    calobj_original = calobj.copy()
    # artificially change the Jones value to permit addition
    calobj2.jones_array[0] = -6
    calobj += calobj2

    # check dimensionality of resulting object
    if caltype == "gain":
        assert calobj.gain_array.shape[-1] == 2
    else:
        assert calobj.delay_array.shape[-1] == 2
    assert sorted(calobj.jones_array) == [-6, -5]

    # test for when total_quality_array is present in first file but not second
    calobj = calobj_original.copy()
    tqa = np.ones(calobj._total_quality_array.expected_shape(calobj))
    tqa2 = np.zeros(calobj2._total_quality_array.expected_shape(calobj2))
    if future_shapes:
        tot_tqa = np.concatenate([tqa, tqa2], axis=2)
    else:
        tot_tqa = np.concatenate([tqa, tqa2], axis=3)
    calobj.total_quality_array = tqa
    calobj += calobj2
    assert np.allclose(
        calobj.total_quality_array,
        tot_tqa,
        rtol=calobj._total_quality_array.tols[0],
        atol=calobj._total_quality_array.tols[1],
    )

    # test for when total_quality_array is present in second file but not first
    calobj = calobj_original.copy()
    tqa = np.zeros(calobj._total_quality_array.expected_shape(calobj))
    tqa2 = np.ones(calobj2._total_quality_array.expected_shape(calobj2))
    if future_shapes:
        tot_tqa = np.concatenate([tqa, tqa2], axis=2)
    else:
        tot_tqa = np.concatenate([tqa, tqa2], axis=3)
    calobj2.total_quality_array = tqa2
    calobj += calobj2
    assert np.allclose(
        calobj.total_quality_array,
        tot_tqa,
        rtol=calobj._total_quality_array.tols[0],
        atol=calobj._total_quality_array.tols[1],
    )

    # test for when total_quality_array is present in both
    calobj = calobj_original.copy()
    tqa = np.ones(calobj._total_quality_array.expected_shape(calobj))
    tqa2 = np.ones(calobj2._total_quality_array.expected_shape(calobj2))
    tqa *= 2
    if future_shapes:
        tot_tqa = np.concatenate([tqa, tqa2], axis=2)
    else:
        tot_tqa = np.concatenate([tqa, tqa2], axis=3)
    calobj.total_quality_array = tqa
    calobj2.total_quality_array = tqa2
    calobj += calobj2
    assert np.allclose(
        calobj.total_quality_array,
        tot_tqa,
        rtol=calobj._total_quality_array.tols[0],
        atol=calobj._total_quality_array.tols[1],
    )

    if caltype == "delay":
        # test for when input_flag_array is present in first file but not second
        calobj = calobj_original.copy()
        ifa = np.zeros(calobj._input_flag_array.expected_shape(calobj)).astype(np.bool_)
        ifa2 = np.ones(calobj2._input_flag_array.expected_shape(calobj2)).astype(
            np.bool_
        )
        if future_shapes:
            tot_ifa = np.concatenate([ifa, ifa2], axis=3)
        else:
            tot_ifa = np.concatenate([ifa, ifa2], axis=4)
        calobj.input_flag_array = ifa
        calobj2.input_flag_array = None
        calobj += calobj2
        assert np.allclose(calobj.input_flag_array, tot_ifa)

        # test for when input_flag_array is present in second file but not first
        calobj = calobj_original.copy()
        ifa = np.ones(calobj._input_flag_array.expected_shape(calobj)).astype(np.bool_)
        ifa2 = np.zeros(calobj2._input_flag_array.expected_shape(calobj2)).astype(
            np.bool_
        )
        if future_shapes:
            tot_ifa = np.concatenate([ifa, ifa2], axis=3)
        else:
            tot_ifa = np.concatenate([ifa, ifa2], axis=4)
        calobj.input_flag_array = None
        calobj2.input_flag_array = ifa2
        calobj += calobj2
        assert np.allclose(calobj.input_flag_array, tot_ifa)

    # Out of order - jones
    calobj = calobj_original.copy()
    calobj2 = calobj_original.copy()
    calobj.jones_array[0] = -6
    calobj += calobj2
    calobj2 = calobj.copy()
    calobj.select(jones=-5)
    calobj.history = calobj_original.history
    assert calobj == calobj_original
    calobj2.select(jones=-6)
    calobj2.jones_array[:] = -5
    calobj2.history = calobj_original.history
    assert calobj2 == calobj_original


@pytest.mark.parametrize("future_shapes", [True, False])
def test_add_jones_multispw(future_shapes, multi_spw_gain):
    """Test adding Jones axes between two UVCal objects"""
    calobj = multi_spw_gain

    if future_shapes:
        calobj.use_future_array_shapes()

    calobj2 = calobj.copy()

    # artificially change the Jones value to permit addition
    calobj2.jones_array[0] = -6
    calobj += calobj2

    # check dimensionality of resulting object
    assert calobj.gain_array.shape[-1] == 2

    assert sorted(calobj.jones_array) == [-6, -5]


@pytest.mark.parametrize("caltype", ["gain", "delay"])
def test_add(caltype, gain_data, delay_data_inputflag):
    """Test miscellaneous aspects of add method"""
    if caltype == "gain":
        calobj = gain_data
    else:
        calobj = delay_data_inputflag

    calobj2 = calobj.copy()

    # test not-in-place addition
    calobj_original = calobj.copy()
    ants1 = np.array([9, 10, 20, 22, 31, 43, 53, 64, 65, 72])
    ants2 = np.array([80, 81, 88, 89, 96, 97, 104, 105, 112])
    calobj.select(antenna_nums=ants1)
    calobj2.select(antenna_nums=ants2)
    calobj_add = calobj + calobj2
    # Check history is correct, before replacing and doing a full object check
    assert uvutils._check_histories(
        calobj_original.history + "  Downselected to specific "
        "antennas using pyuvdata. Combined "
        "data along antenna axis using pyuvdata.",
        calobj_add.history,
    )
    calobj_add.history = calobj_original.history
    assert calobj_add == calobj_original

    # test history concatenation
    calobj.history = calobj_original.history
    if caltype == "gain":
        calobj2.history = "Some random history string OMNI_RUN:"
    else:
        calobj2.history = "Some random history string firstcal.py"
    new_cal = calobj + calobj2

    additional_history = "Some random history string"
    assert uvutils._check_histories(
        calobj_original.history + " Combined data along antenna axis "
        "using pyuvdata. Unique part of next object history follows.  "
        + additional_history,
        new_cal.history,
    )

    new_cal = calobj.__add__(calobj2, verbose_history=True)
    assert uvutils._check_histories(
        calobj_original.history + " Combined data along antenna axis "
        "using pyuvdata. Next object history follows.  " + calobj2.history,
        new_cal.history,
    )


def test_add_multiple_axes(gain_data):
    """Test addition along multiple axes"""
    calobj = gain_data
    calobj2 = calobj.copy()

    ants1 = np.array([9, 10, 20, 22, 31, 43, 53, 64, 65, 72])
    ants2 = np.array([80, 81, 88, 89, 96, 97, 104, 105, 112])
    freqs1 = calobj.freq_array[0, np.arange(0, 5)]
    freqs2 = calobj.freq_array[0, np.arange(5, 10)]
    n_times2 = calobj.Ntimes // 2
    times1 = calobj.time_array[:n_times2]
    times2 = calobj.time_array[n_times2:]
    # artificially change the Jones value to permit addition
    calobj2.jones_array[0] = -6

    # perform select
    calobj.select(antenna_nums=ants1, frequencies=freqs1, times=times1)
    calobj2.select(antenna_nums=ants2, frequencies=freqs2, times=times2)

    calobj += calobj2

    # check resulting dimensionality
    assert len(calobj.ant_array) == 19
    assert len(calobj.freq_array[0, :]) == 10
    assert len(calobj.time_array) == calobj.Ntimes
    assert len(calobj.jones_array) == 2


@pytest.mark.parametrize("caltype", ["gain", "delay"])
def test_add_errors(caltype, gain_data, delay_data, multi_spw_gain):
    """Test behavior that will raise errors"""
    if caltype == "gain":
        calobj = gain_data
    else:
        calobj = delay_data

    calobj2 = calobj.copy()

    # test addition of two identical objects
    with pytest.raises(
        ValueError, match="These objects have overlapping data and cannot be combined."
    ):
        calobj.__add__(calobj2)

    # test addition of UVCal and non-UVCal object (empty list)
    with pytest.raises(
        ValueError, match="Only UVCal ",
    ):
        calobj.__add__([])

    # test compatibility param mismatch
    calobj2.telescope_name = "PAPER"
    with pytest.raises(
        ValueError, match="Parameter telescope_name does not match",
    ):
        calobj.__add__(calobj2)

    # test array shape mismatch
    calobj2 = calobj.copy()
    calobj2.use_future_array_shapes()
    with pytest.raises(
        ValueError,
        match="Both objects must have the same `future_array_shapes` parameter.",
    ):
        calobj + calobj2

    # test flex_spw mismatch
    with pytest.raises(
        ValueError,
        match="To combine these data, flex_spw must be set to the same value",
    ):
        gain_data + multi_spw_gain


def test_jones_warning(gain_data):
    """Test having non-contiguous Jones elements"""
    calobj = gain_data
    calobj2 = calobj.copy()

    calobj2.jones_array[0] = -6
    calobj += calobj2
    calobj2.jones_array[0] = -8
    with uvtest.check_warnings(
        UserWarning, match="Combined Jones elements",
    ):
        calobj.__iadd__(calobj2)
    assert sorted(calobj.jones_array) == [-8, -6, -5]


@pytest.mark.parametrize("future_shapes", [True, False])
def test_frequency_warnings(future_shapes, gain_data):
    """Test having uneven or non-contiguous frequencies"""
    # test having unevenly spaced frequency separations
    calobj = gain_data

    if future_shapes:
        calobj.use_future_array_shapes()

    calobj2 = calobj.copy()

    go1 = calobj.copy()
    go2 = calobj2.copy()
    if future_shapes:
        freqs1 = calobj.freq_array[np.arange(0, 5)]
        freqs2 = calobj2.freq_array[np.arange(5, 10)]
    else:
        freqs1 = calobj.freq_array[0, np.arange(0, 5)]
        freqs2 = calobj2.freq_array[0, np.arange(5, 10)]

    calobj.select(frequencies=freqs1)
    calobj2.select(frequencies=freqs2)

    # change the last frequency bin to be smaller than the others
    if future_shapes:
        df = calobj2.freq_array[-1] - calobj2.freq_array[-2]
        calobj2.freq_array[-1] = calobj2.freq_array[-2] + df / 2
    else:
        df = calobj2.freq_array[0, -1] - calobj2.freq_array[0, -2]
        calobj2.freq_array[0, -1] = calobj2.freq_array[0, -2] + df / 2
    with uvtest.check_warnings(
        UserWarning, match="Combined frequencies are not evenly spaced"
    ):
        calobj.__iadd__(calobj2)

    assert calobj.freq_array.size == calobj.Nfreqs

    # now check having "non-contiguous" frequencies
    calobj = go1.copy()
    calobj2 = go2.copy()
    calobj.select(frequencies=freqs1)
    calobj2.select(frequencies=freqs2)

    # artificially space out frequencies
    calobj.freq_array *= 10
    calobj2.freq_array *= 10
    with uvtest.check_warnings(
        UserWarning,
        match="Combined frequencies are separated by more than their channel width",
    ):
        calobj.__iadd__(calobj2)

    freqs1 *= 10
    freqs2 *= 10
    freqs = np.concatenate([freqs1, freqs2])
    if future_shapes:
        freq_arr = calobj.freq_array
    else:
        freq_arr = calobj.freq_array[0, :]
    assert np.allclose(
        freq_arr,
        freqs,
        rtol=calobj._freq_array.tols[0],
        atol=calobj._freq_array.tols[1],
    )


def test_parameter_warnings(gain_data):
    """Test changing a parameter that will raise a warning"""
    # change observer and select frequencies
    calobj = gain_data
    calobj2 = calobj.copy()

    calobj2.observer = "mystery_person"
    freqs1 = calobj.freq_array[0, np.arange(0, 5)]
    freqs2 = calobj2.freq_array[0, np.arange(5, 10)]
    calobj.select(frequencies=freqs1)
    calobj2.select(frequencies=freqs2)
    with uvtest.check_warnings(
        UserWarning, match="UVParameter observer does not match"
    ):
        calobj.__iadd__(calobj2)

    freqs = np.concatenate([freqs1, freqs2])
    assert np.allclose(
        calobj.freq_array,
        freqs,
        rtol=calobj._freq_array.tols[0],
        atol=calobj._freq_array.tols[1],
    )


@pytest.mark.parametrize("caltype", ["gain", "delay"])
def test_multi_files(caltype, gain_data, delay_data_inputflag, tmp_path):
    """Test read function when multiple files are included"""
    if caltype == "gain":
        calobj = gain_data
    else:
        calobj = delay_data_inputflag

    calobj2 = calobj.copy()

    calobj_full = calobj.copy()
    n_times2 = calobj.Ntimes // 2
    # Break up delay object into two objects, divided in time
    times1 = calobj.time_array[:n_times2]
    times2 = calobj.time_array[n_times2:]
    calobj.select(times=times1)
    calobj2.select(times=times2)
    # Write those objects to files
    f1 = str(tmp_path / "read_multi1.calfits")
    f2 = str(tmp_path / "read_multi2.calfits")
    calobj.write_calfits(f1, clobber=True)
    calobj2.write_calfits(f2, clobber=True)
    # Read both files together
    calobj.read_calfits([f1, f2])
    assert uvutils._check_histories(
        calobj_full.history + "  Downselected to specific times"
        " using pyuvdata. Combined data "
        "along time axis using pyuvdata.",
        calobj.history,
    )
    assert calobj.filename == ["read_multi1.calfits", "read_multi2.calfits"]
    calobj.history = calobj_full.history
    assert calobj == calobj_full

    # check metadata only read
    calobj.read_calfits([f1, f2], read_data=False)
    calobj_full_metadata_only = calobj_full.copy(metadata_only=True)

    calobj.history = calobj_full_metadata_only.history
    assert calobj == calobj_full_metadata_only


@pytest.mark.parametrize("future_shapes", [True, False])
def test_uvcal_get_methods(future_shapes, gain_data):
    # load data
    uvc = gain_data

    if future_shapes:
        uvc.use_future_array_shapes()

    # test get methods: add in a known value and make sure it is returned
    key = (10, "Jee")
    uvc.gain_array[1] = 0.0
    gain_arr = uvc.get_gains(key)
    flag_arr = uvc.get_flags(key)
    quality_arr = uvc.get_quality(key)

    # test shapes
    assert np.all(np.isclose(gain_arr, 0.0))
    assert gain_arr.shape == (uvc.Nfreqs, uvc.Ntimes)
    assert flag_arr.shape == (uvc.Nfreqs, uvc.Ntimes)
    assert quality_arr.shape == (uvc.Nfreqs, uvc.Ntimes)

    # test against by-hand indexing
    if future_shapes:
        expected_array = uvc.gain_array[
            uvc.ant_array.tolist().index(10), :, :, uvc.jones_array.tolist().index(-5),
        ]
    else:
        expected_array = uvc.gain_array[
            uvc.ant_array.tolist().index(10),
            0,
            :,
            :,
            uvc.jones_array.tolist().index(-5),
        ]
    np.testing.assert_array_almost_equal(gain_arr, expected_array)

    # test variable key input
    gain_arr2 = uvc.get_gains(*key)
    np.testing.assert_array_almost_equal(gain_arr, gain_arr2)
    gain_arr2 = uvc.get_gains(key[0])
    np.testing.assert_array_almost_equal(gain_arr, gain_arr2)
    gain_arr2 = uvc.get_gains(key[:1])
    np.testing.assert_array_almost_equal(gain_arr, gain_arr2)
    gain_arr2 = uvc.get_gains(10, -5)
    np.testing.assert_array_almost_equal(gain_arr, gain_arr2)
    gain_arr2 = uvc.get_gains(10, "x")
    np.testing.assert_array_almost_equal(gain_arr, gain_arr2)

    # check has_key
    assert uvc._has_key(antnum=10)
    assert uvc._has_key(jpol="Jee")
    assert uvc._has_key(antnum=10, jpol="Jee")
    assert not uvc._has_key(antnum=10, jpol="Jnn")
    assert not uvc._has_key(antnum=101, jpol="Jee")

    # test exceptions
    pytest.raises(ValueError, uvc.get_gains, 1)
    pytest.raises(ValueError, uvc.get_gains, (10, "Jnn"))
    uvc.cal_type = "delay"
    pytest.raises(ValueError, uvc.get_gains, 10)


def test_write_read_optional_attrs(gain_data, tmp_path):
    # read a test file
    cal_in = gain_data

    # set some optional parameters
    cal_in.gain_scale = "Jy"
    cal_in.sky_field = "GLEAM"

    # write
    write_file_calfits = str(tmp_path / "test.calfits")
    cal_in.write_calfits(write_file_calfits, clobber=True)

    # read and compare
    cal_in2 = UVCal()
    cal_in2.read_calfits(write_file_calfits)
    assert cal_in == cal_in2


@pytest.mark.parametrize("future_shapes", [True, False])
@pytest.mark.parametrize("caltype", ["gain", "delay", "unknown", None])
def test_copy(future_shapes, gain_data, delay_data_inputflag, caltype):
    """Test the copy method"""
    if caltype == "gain":
        uv_object = gain_data
    elif caltype == "delay":
        uv_object = delay_data_inputflag
    else:
        uv_object = gain_data
        uv_object._set_unknown_cal_type()
        uv_object.cal_type = caltype

    if future_shapes:
        uv_object.use_future_array_shapes()

    uv_object_copy = uv_object.copy()
    assert uv_object_copy == uv_object

    uv_object_copy = uv_object.copy(metadata_only=True)
    assert uv_object_copy.metadata_only

    for name in uv_object._data_params:
        setattr(uv_object, name, None)
    assert uv_object_copy == uv_object

    uv_object_copy = uv_object.copy()
    assert uv_object_copy == uv_object

    return


@pytest.mark.parametrize("antnamefix", ["all", "partial"])
def test_match_antpos_antname(gain_data, antnamefix, tmp_path):

    # fix the antenna names in the uvcal object to match telescope object
    new_names = np.array(
        [name.replace("ant", "HH") for name in gain_data.antenna_names]
    )
    if antnamefix == "all":
        gain_data.antenna_names = new_names
    else:
        gain_data.antenna_names[0 : gain_data.Nants_telescope // 2] = new_names[
            0 : gain_data.Nants_telescope // 2
        ]

    # remove the antenna_positions to test matching them on read
    gain_data2 = gain_data.copy()
    gain_data2.antenna_positions = None

    write_file_calfits = str(tmp_path / "test.calfits")
    with uvtest.check_warnings(
        DeprecationWarning,
        match="The antenna_positions parameter is not set. It will be a required "
        "parameter starting in pyuvdata version 2.3",
    ):
        gain_data2.write_calfits(write_file_calfits)

    with uvtest.check_warnings(
        UserWarning, "antenna_positions is not set. Using known values for HERA."
    ):
        gain_data2.read_calfits(write_file_calfits)

    assert gain_data2.antenna_positions is not None
    assert gain_data == gain_data2


@pytest.mark.parametrize("modtype", ["rename", "swap"])
def test_set_antpos_from_telescope_errors(gain_data, modtype, tmp_path):
    """Test that setting antenna positions doesn't happen if ants don't match."""
    # fix the antenna names in the uvcal object to match telescope object
    new_names = np.array(
        [name.replace("ant", "HH") for name in gain_data.antenna_names]
    )
    gain_data.antenna_names = new_names

    if modtype == "rename":
        # change the name & number of one of the antennas
        orig_num = gain_data.antenna_numbers[0]
        gain_data.antenna_names[0] = "HH400"
        gain_data.antenna_numbers[0] = 400
        gain_data.ant_array[np.where(gain_data.ant_array == orig_num)[0]] = 400
    else:
        # change the name of one antenna and swap the number with a different antenna
        orig_num = gain_data.antenna_numbers[0]
        gain_data.antenna_names[0] = "HH400"
        gain_data.antenna_numbers[0] = gain_data.antenna_numbers[1]
        gain_data.antenna_numbers[1] = orig_num

    # remove the antenna_positions to test matching them on read
    gain_data2 = gain_data.copy()
    gain_data2.antenna_positions = None

    write_file_calfits = str(tmp_path / "test.calfits")
    with uvtest.check_warnings(
        DeprecationWarning,
        match="The antenna_positions parameter is not set. It will be a required "
        "parameter starting in pyuvdata version 2.3",
    ):
        gain_data2.write_calfits(write_file_calfits)

    with uvtest.check_warnings(
        [UserWarning, DeprecationWarning],
        match=[
            "Not all antennas have positions in the telescope object. "
            "Not setting antenna_positions.",
            "The antenna_positions parameter is not set. It will be a required "
            "parameter starting in pyuvdata version 2.3",
        ],
    ):
        gain_data2.read_calfits(write_file_calfits)

    assert gain_data2.antenna_positions is None
