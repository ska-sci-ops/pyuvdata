# - * - coding: utf-8 - * -
"""Class for reading MWA correlator FITS files

"""
from astropy.io import fits
import numpy as np
import warnings
from astropy.time import Time

from . import UVData
from . import utils as uvutils


def input_output_mapping():
    '''
    Builds a mapping dictionary from the pfb output numbers (the correlator
    indices for antenna number and polarization) to the pfb input numbers.
    These input numbers can be mapped to antenna numbers using metadata.
    '''
    # this comes from mwa_build_lfiles/mwac_utils.c
    # inputs are mapped to the indices of pfb_mapper as follows
    # (from mwa_build_lfiles/antenna_mapping.h):
    # floor(index/4) + index%4 * 16 = input
    pfb_mapper = [0, 16, 32, 48, 1, 17, 33, 49, 2, 18, 34, 50, 3, 19, 35, 51,
                  4, 20, 36, 52, 5, 21, 37, 53, 6, 22, 38, 54, 7, 23, 39, 55,
                  8, 24, 40, 56, 9, 25, 41, 57, 10, 26, 42, 58, 11, 27, 43, 59,
                  12, 28, 44, 60, 13, 29, 45, 61, 14, 30, 46, 62, 15, 31, 47,
                  63]
    # pfb_mapper maps the first 64 inputs; build a mapper for all 256 inputs
    pfb_inputs_to_outputs = {}
    for p in range(4):
        for i in range(64):
            pfb_inputs_to_outputs[pfb_mapper[i] + p * 64] = p * 64 + i
    return pfb_inputs_to_outputs


class MWACorrFITS(UVData):
    """
    Defines a MWA correlator fits-specific subclass of UVData for reading MWA
    correlator fits files. This class should not be interacted with directly,
    instead use the read_mwa_corr_fits method on the UVData class.
    """
    def read_mwa_corr_fits(self, filelist, use_cotter_flags=False,
                           run_check=True, check_extra=True,
                           run_check_acceptability=True):
        """
        Read in data from a list of MWA correlator fits files.

        Args:
            filelist : The list of MWA correlator files to read from. Currently
                only a single observation is supported. Must include one
                metafits file.
            run_check : Option to check for the existence and proper shapes of
                parameters after reading in the file. Default is True.
            check_extra : Option to check optional parameters as well as
                required ones. Default is True.
            run_check_acceptability: Option to check acceptable range of the
                values of parameters after reading in the file. Default is True
        """

        metafits_file = None
        file_dict = {}
        start_time = 0.0
        end_time = 0.0
        included_file_nums = []
        cotter_warning = False
        num_fine_chans = 0

        # TOOD: what (if anything) to do with the metafits_ppds file?
        # iterate through files and organize
        # create a list of included coarse channels
        # find the first and last times that have data
        for file in filelist:
            if file.lower().endswith('.metafits'):
                # check that have a metafits file
                # TODO: figure out what to do with multiple metafits files
                # for now, force only one metafits file
                if metafits_file is not None:
                    raise ValueError('multiple metafits files in filelist')
                metafits_file = file
            # organize data files
            elif file.lower().endswith('00.fits') or file.lower().endswith('01.fits'):
                # get the file number from the file name;
                # this will later be mapped to a coarse channel
                file_num = int(file.split('_')[-2][-2:])
                if file_num not in included_file_nums:
                    included_file_nums.append(file_num)
                with fits.open(file) as data:
                    # check headers for first and last times containing data
                    first_time = data[1].header['TIME'] + data[1].header['MILLITIM'] / 1000.0
                    last_time = data[-1].header['TIME'] + data[-1].header['MILLITIM'] / 1000.0
                    if start_time == 0.0:
                        start_time = first_time
                    elif start_time > first_time:
                        start_time = first_time
                    if end_time < last_time:
                        end_time = last_time
                    # get number of fine channels
                    if 'NAXIS2' in data[1].header.keys():
                        if num_fine_chans == 0:
                            num_fine_chans = data[1].header['NAXIS2']
                        elif num_fine_chans != data[1].header['NAXIS2']:
                            raise ValueError('files submitted have different fine \
                            channel widths')
                    # have to add this for the test file to work
                    else:
                        num_fine_chans = 1

                # organize files
                if 'data' not in file_dict.keys():
                    file_dict['data'] = [file]
                else:
                    file_dict['data'].append(file)
            # look for flag files
            elif file.lower().endswith('.mwaf'):
                if use_cotter_flags is False and cotter_warning is False:
                    warnings.warn('mwaf files submitted but will not be used. \
                    User might wish to rerun with use_cotter_flags=True')
                    cotter_warning = True
                elif 'flags' not in file_dict.keys():
                    file_dict['flags'] = [file]
                else:
                    file_dict['flags'].append(file)
            else:
                continue

        # checks:
        if metafits_file is None:
            raise ValueError('no metafits files submitted')
        if 'data' not in file_dict.keys():
            raise ValueError('no fits files submitted')
        if 'flags' not in file_dict.keys():
            warnings.warn('no flag files submitted')
        # TODO: think about what checks make sense for missing data

        # first set parameters that are always true
        self.Nspws = 1
        self.spw_array = np.array([0])
        self.phase_type = 'drift'
        self.vis_units = 'uncalib'
        self.Npols = 4

# ==============================================================================
#         #set antenna array location latitude (radians), longitude (radians),
#         #altitude
#         #(meters above sea level)
#         lat = -26.703319 * np.pi/180
#         lon = 116.67081 * np.pi/180
#         alt = 377
#         self.telescope_location_lat_lon_alt=[lat,lon,alt]
# ==============================================================================

        # get information from metafits file
        with fits.open(metafits_file, memmap=True) as meta:
            meta_hdr = meta[0].header

            # get a list of coarse channels
            coarse_chans = meta_hdr['CHANNELS'].split(',')
            coarse_chans = np.array([int(i) for i in coarse_chans])

            # integration time in seconds
            int_time = meta_hdr['INTTIME']

            # get parameters from header
            # this assumes no averaging by this code so will need to be updated
            self.channel_width = float(meta_hdr['FINECHAN'] * 1000)
            self.history = str(meta_hdr['HISTORY']) + '\n AIPS WTSCAL = 1.0 \n'
            # TODO: figure out 'AIPS WTSCAL = 1.0'
            if not uvutils._check_history_version(self.history,
                                                  self.pyuvdata_version_str):
                self.history += self.pyuvdata_version_str
            self.instrument = meta_hdr['TELESCOP']
            self.telescope_name = meta_hdr['TELESCOP']
            self.object_name = meta_hdr['FILENAME']
            # TODO: remove these keys and store remaining keys in extra keywords

            # get antenna data from metafits file table
            meta_tbl = meta[1].data

            # because of polarization, each antenna # is listed twice
            antenna_numbers = meta_tbl['Antenna'][1::2]
            antenna_names = meta_tbl['TileName'][1::2]
            antenna_flags = meta_tbl['Flag'][1::2]

            # get antenna postions in enu coordinates
            antenna_positions = np.zeros((len(antenna_numbers), 3))
            antenna_positions[:, 0] = meta_tbl['East'][1::2]
            antenna_positions[:, 1] = meta_tbl['North'][1::2]
            antenna_positions[:, 2] = meta_tbl['Height'][1::2]

            # TODO: self.antenna_diameters
            # TODO: self.x_orientation

        # reorder antenna parameters from metafits ordering
        reordered_inds = antenna_numbers.argsort()
        self.antenna_numbers = antenna_numbers[reordered_inds]
        self.antenna_names = list(antenna_names[reordered_inds])
        antenna_positions = antenna_positions[reordered_inds, :]
        antenna_flags = antenna_flags[reordered_inds]

        # find flagged antenna
        flagged_ants = self.antenna_numbers[np.where(antenna_flags == 1)]

        # set parameters from other parameters
        self.Nants_data = len(self.antenna_numbers)
        self.Nants_telescope = len(self.antenna_numbers)
        self.Nbls = int(len(self.antenna_numbers) * (len(self.antenna_numbers) + 1) / 2.0)

        # get telescope parameters
        self.set_telescope_params()

        # build time array of centers
        time_array = np.arange(start_time + int_time / 2.0, end_time
                               + int_time / 2.0 + int_time, int_time)

        # convert from unix to julian times
        julian_time_array = [Time(i, format='unix', scale='utc').jd
                             for i in time_array]

        # convert to integers
        float_time_array = np.array([float(i) for i in julian_time_array])
        # build into time array
        self.time_array = np.repeat(float_time_array, self.Nbls)

        self.Ntimes = len(time_array)

        self.Nblts = int(self.Nbls * self.Ntimes)

        lat, lon, alt = self.telescope_location_lat_lon_alt_degrees

        # convert times to lst
        self.lst_array = uvutils.get_lst_for_time(self.time_array, lat, lon, alt)

        # assumes no averaging
        self.integration_time = np.array([int_time for i in range(self.Nblts)])

        # convert antenna positions from enu to ecef
        # TODO: ask Bryna does this work? antenna positions are "relative to
        # the centre of the array in local topocentric \"east\", \"north\",
        # \"height\". Units are meters."
        antenna_positions_ecef = uvutils.ECEF_from_ENU(antenna_positions, lat, lon, alt)
        # convert to ITRF
        self.antenna_positions = antenna_positions_ecef - self.telescope_location

        # make initial antenna arrays, where ant_1 <= ant_2
        ant_1_array = []
        ant_2_array = []
        for i in range(self.Nants_telescope):
            for j in range(i, self.Nants_telescope):
                ant_1_array.append(i)
                ant_2_array.append(j)

        self.ant_1_array = np.tile(np.array(ant_1_array), self.Ntimes)
        self.ant_2_array = np.tile(np.array(ant_2_array), self.Ntimes)

        self.baseline_array = \
            self.antnums_to_baseline(self.ant_1_array, self.ant_2_array)

        # create self.uvw_array
        self.set_uvws_from_antenna_positions(allow_phasing=False)

        # coarse channel mapping:
        # channels in group 0-128 go in order; channels in group 129-155 go in
        # reverse order
        # that is, if the lowest channel is 127, it will be assigned to the
        # first file
        # channel 128 will be assigned to the second file
        # then the highest channel will be assigned to the third file
        # and the next hightest channel assigned to the fourth file, and so on
        count = 0
        # count the number of channels that are in group 0-128
        for i in coarse_chans:
            if i <= 128:
                count += 1
        # map all file numbers to coarse channel numbers
        file_nums_to_coarse = {i + 1: coarse_chans[i] if i < count else
                               coarse_chans[(len(coarse_chans) + count - i - 1)]
                               for i in range(len(coarse_chans))}

        # find which coarse channels are actually included
        included_coarse_chans = []
        for i in included_file_nums:
            included_coarse_chans.append(file_nums_to_coarse[i])
        included_coarse_chans = sorted(included_coarse_chans)

        # count the number of included coarse channels that are in group 0-128
        count = 0
        for i in included_coarse_chans:
            if i <= 128:
                count += 1
        # map included file numbers to an index that orders them
        file_nums_to_index = {i + 1: i if i < count else (len(included_coarse_chans)
                              + count - i - 1) for i in range(len(included_coarse_chans))}

        # check that coarse channels are contiguous.
        # TODO: look at a data file where the coarse channels aren't contiguous to make sure this works
        chans = np.array([int(i) for i in included_coarse_chans])
        for i in np.diff(chans):
            if i != 1:
                warnings.warn('coarse channels are not contiguous \
                for this observation')
                break

        # warn user if not all coarse channels are included
        if len(included_coarse_chans) != len(coarse_chans):
            warnings.warn('some coarse channel files were not submitted')

        # build frequency array
        self.Nfreqs = len(included_coarse_chans) * num_fine_chans
        self.freq_array = np.zeros((self.Nspws, self.Nfreqs))

        # each coarse channel is split into 128 fine channels of width 10 kHz.
        # The first fine channel for each coarse channel is centered on the
        # lower bound frequency of that channel and its center frequency is
        # computed as fine_center = coarse_channel_number * 1280-640 (kHz).
        # If the fine channels have been averaged (added) by some factor, the
        # center of the resulting channel is found by averaging the centers of
        # the first and last fine channels it is made up of.
        # That is, avg_fine_center=(lowest_fine_center+highest_fine_center)/2
        # where highest_fine_center=lowest_fine_center+(avg_factor-1)*10 kHz
        # so avg_fine_center=(lowest_fine_center+lowest_fine_center+(avg_factor-1)*10)/2
        #                   =lowest_fine_center+((avg_factor-1)*10)/2
        #                   =lowest_fine_center+offset
        # Calculate offset=((avg_factor-1)*10)/2 to build the frequency array
        avg_factor = self.channel_width / 10000
        width = self.channel_width / 1000
        offset = (avg_factor - 1) * width / 2.0

        for i in range(len(included_coarse_chans)):
            # get the lowest fine freq of the coarse channel (kHz)
            lower_fine_freq = included_coarse_chans[i] * 1280 - 640
            # find the center of the lowest averaged channel
            first_center = lower_fine_freq + offset
            # add the channel centers for this coarse channel into
            # the frequency array (converting from kHz to Hz)
            self.freq_array[0, int(i * num_fine_chans):int((i + 1) * num_fine_chans)] = \
                np.arange(first_center, first_center + num_fine_chans * width, width) * 1000

        # initialize a flag array; as data is read in unflag that data
        # this way missing data is automatically flagged
        flag_dump = np.full((self.Ntimes, self.Nfreqs, self.Nbls * self.Npols), True)
        # read data into an array with dimensions (time, uv, baselines*pols)
        data_dump = np.zeros((self.Ntimes, self.Nfreqs, self.Nbls * self.Npols), dtype=np.complex64)
        # read data files
        for file in file_dict['data']:
            # get the file number from the file name
            file_num = int(file.split('_')[-2][-2:])
            # map file number to frequency index
            freq_ind = file_nums_to_index[file_num] * num_fine_chans
            with fits.open(file, memmap=False, do_not_scale_image_data=False) as hdu_list:
                # count number of times
                end_list = len(hdu_list)
                for i in range(1, end_list):
                    time = hdu_list[i].header['TIME'] + hdu_list[i].header['MILLITIM'] / 1000.0 + int_time / 2.0
                    time_ind = np.where(time_array == time)[0][0]
                    # dump data into matrix
                    # and take data from real to complex numbers
                    data_dump[time_ind, freq_ind:freq_ind + num_fine_chans, :] = \
                        hdu_list[i].data[..., 0::2] + 1j * hdu_list[i].data[..., 1::2]
                    # unflag where data is
                    flag_dump[time_ind, freq_ind:freq_ind + num_fine_chans, :] = False

        # polarizations are ordered yy, yx, xy, xx
        self.polarization_array = np.array([-6, -8, -7, -5])
        
        # initialize matrices for data reordering
        self.nsample_array = np.zeros((self.Nblts, self.Nspws, self.Nfreqs, self.Npols), dtype=np.float32)
        self.data_array = np.zeros((self.Ntimes, self.Nbls, self.Nfreqs, self.Npols), dtype=np.complex64)
        self.flag_array = np.full((self.Ntimes, self.Nbls, self.Nfreqs, self.Npols), True)
        # build mapper from antenna numbers and polarizations to pfb inputs
        corr_ants_to_pfb_inputs = {}
        for i in range(len(antenna_numbers)):
            for p in range(2):
                corr_ants_to_pfb_inputs[(antenna_numbers[i], p)] = 2 * i + p

        # for mapping, start with a pair of antennas/polarizations
        # this is the pair we want to find the data for
        # map the pair to the corresponding pfb input indices
        # map the pfb input indices to the pfb output indices
        # these are the indices for the data corresponding to the initial antenna/pol pair
        pfb_inputs_to_outputs = input_output_mapping()
        for ant1 in range(128):
            for ant2 in range(ant1, 128):
                for p1 in range(2):
                    for p2 in range(2):
                        # generate the indices in self.data_array for this combination
                        # baselines are ordered (0,0),(0,1),...,(0,127),(1,1),.....
                        # polarizion of 0 (1) corresponds to y (x)
                        pol_ind = int(2 * p1 + p2)
                        bls_ind = int(128 * ant1 - ant1 * (ant1 + 1) / 2 + ant2)
                        # find the pfb input indices for this combination
                        (ind1_1, ind1_2) = (corr_ants_to_pfb_inputs[(ant1, p1)],
                                            corr_ants_to_pfb_inputs[(ant2, p2)])
                        # find the pfb output indices
                        (ind2_1, ind2_2) = (pfb_inputs_to_outputs[(ind1_1)],
                                            pfb_inputs_to_outputs[(ind1_2)])
                        out_ant1 = int(ind2_1 / 2)
                        out_ant2 = int(ind2_2 / 2)
                        out_p1 = ind2_1 % 2
                        out_p2 = ind2_2 % 2
                        # the correlator has antenna 1 >= antenna2,
                        # so check if ind2_1 and ind2_2 satisfy this
                        if out_ant1 < out_ant2:
                            # get the index for the data
                            data_index = int(2 * out_ant2 * (out_ant2 + 1) + 4 * out_ant1 + 2 * out_p2 + out_p1)
                            # need to take the complex conjugate of the data
                            self.data_array[:, bls_ind, :, pol_ind] = np.conj(data_dump[:, :, data_index])
                        else:
                            data_index = int(2 * out_ant1 * (out_ant1 + 1) + 4 * out_ant2 + 2 * out_p1 + out_p2)
                            self.data_array[:, bls_ind, :, pol_ind] = data_dump[:, :, data_index]
                        # reorder flags
                        self.flag_array[:, bls_ind, :, pol_ind] = flag_dump[:, :, data_index]

        # add spectral window index
        self.data_array = self.data_array[:, :, np.newaxis, :, :]
        self.flag_array = self.flag_array[:, :, np.newaxis, :, :]

        # should have nsample_array = 1 where data is present
        self.nsample_array = np.where(self.flag_array, self.nsample_array, 1)

        # generage baseline flags for flagged ants
        baseline_flags = np.full(self.Nbls, False)
        for ant1 in range(128):
            for ant2 in range(ant1, 128):
                if ant1 in flagged_ants or ant2 in flagged_ants:
                    baseline_flags[int(128 * ant1 - ant1 * (ant1 + 1) / 2 + ant2)] = True

        self.flag_array[:, np.where(baseline_flags is True), :, :] = True

        # combine baseline and time axes
        self.data_array = self.data_array.reshape((self.Nblts, self.Nspws, self.Nfreqs, self.Npols))
        self.flag_array = self.flag_array.reshape((self.Nblts, self.Nspws, self.Nfreqs, self.Npols))

        # TODO: add support for cotter flag files
