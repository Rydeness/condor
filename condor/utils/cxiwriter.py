# -----------------------------------------------------------------------------------------------------
# CONDOR
# Simulator for diffractive single-particle imaging experiments with X-ray lasers
# http://xfel.icm.uu.se/condor/
# -----------------------------------------------------------------------------------------------------
# Copyright 2016 Max Hantke, Filipe R.N.C. Maia, Tomas Ekeberg
# Condor is distributed under the terms of the BSD 2-Clause License
# -----------------------------------------------------------------------------------------------------
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# -----------------------------------------------------------------------------------------------------
# General note:
# All variables are in SI units by default. Exceptions explicit by variable name.
# -----------------------------------------------------------------------------------------------------
from __future__ import print_function, absolute_import # Compatibility with python 2 and 3
import numpy, os
  
import logging
logger = logging.getLogger(__name__)

from .log import log_and_raise_error,log_warning,log_info,log_debug

try:
    import h5py
except ImportError:
    log_warning(logger, "Could not import h5py.")

class CXIWriter:
    def __init__(self, filename, chunksize=2, gzip_compression=False):
        self._filename = os.path.expandvars(filename)
        if os.path.exists(filename):
            log_warning(logger, "File %s exists and is being overwritten" % filename)
        self._f = h5py.File(filename, "w")
        self._i = 0
        self._chunksize = chunksize
        self._create_dataset_kwargs = {}
        if gzip_compression:
            self._create_dataset_kwargs["compression"] = "gzip"

    def write(self, D):
        self._write_without_iterate(D)
        self._f.flush()
        self._i += 1
        
    def _write_without_iterate(self, D, group_prefix="/"):
        for k in D.keys():
            if isinstance(D[k],dict):
                group_prefix_new = group_prefix + k + "/"
                log_debug(logger, "Writing group %s" % group_prefix_new)
                if k not in self._f[group_prefix]:
                    self._f.create_group(group_prefix_new)
                self._write_without_iterate(D[k], group_prefix_new)
            else:
                name = group_prefix + k
                log_debug(logger, "Writing dataset %s" % name)
                data = D[k]
                if k not in self._f[group_prefix]:
                    if numpy.isscalar(data):
                        maxshape = (None,)
                        shape = (self._chunksize,)
                        if (isinstance(data, str)):
                            dtype = numpy.dtype(type(data.encode('utf8')))
                        else:
                            dtype = numpy.dtype(type(data))
                        if dtype == "S":
                            dtype = h5py.vlen_dtype(str)
                        axes = "experiment_identifier:value"
                    else:
                        data = numpy.asarray(data)
                        try:
                            h5py.h5t.py_create(data.dtype, logical=1)
                        except TypeError:
                            log_warning(logger, "Could not save dataset %s. Conversion to numpy array failed" % name)
                            continue
                        maxshape = tuple([None]+list(data.shape))
                        shape = tuple([self._chunksize]+list(data.shape))
                        dtype = data.dtype
                        ndim = data.ndim
                        axes = "experiment_identifier"
                        if ndim == 1: axes = axes + ":x"
                        elif ndim == 2: axes = axes + ":y:x"
                        elif ndim == 3: axes = axes + ":z:y:x"
                    log_debug(logger, "Create dataset %s [shape=%s, dtype=%s]" % (name,str(shape),str(dtype)))
                    self._f.create_dataset(name, shape, maxshape=maxshape, dtype=dtype, **self._create_dataset_kwargs)
                    self._f[name].attrs.modify("axes",[axes.encode('utf8')])
                if self._f[name].shape[0] <= self._i:
                    if numpy.isscalar(data):
                        data_shape = []
                    else:
                        data_shape = data.shape
                    new_shape = tuple([self._chunksize*(self._i/self._chunksize+1)]+list(data_shape))
                    log_debug(logger, "Resize dataset %s [old shape: %s, new shape: %s]" % (name,str(self._f[name].shape),str(new_shape)))
                    self._f[name].resize(new_shape)
                log_debug(logger, "Write to dataset %s at stack position %i" % (name, self._i))
                if numpy.isscalar(data):
                    self._f[name][self._i] = data
                else:
                    self._f[name][self._i,:] = data[:]

    def _shrink_stacks(self, group_prefix="/"):
        for k in self._f[group_prefix].keys():
            name = group_prefix + k
            if isinstance(self._f[name], h5py.Dataset):
                log_debug(logger, "Shrinking dataset %s to stack length %i" % (name, self._i))
                s = list(self._f[name].shape)
                s.pop(0)
                s.insert(0, self._i)
                s = tuple(s)
                self._f[name].resize(s)
            else:
                self._shrink_stacks(name + "/")
                    
    def close(self):
        self._shrink_stacks()
        log_debug(logger, "Closing file %s" % self._filename)
        self._f.close()


def read_map(filename):
    # CCP4 map file format
    # http://www.ccp4.ac.uk/html/maplib.html
    with open(filename, "rb") as f:
        # 1024 bytes header
        header_buf = f.read(1024)
        #1      NC              # of Columns    (fastest changing in map)
        #2      NR              # of Rows
        #3      NS              # of Sections   (slowest changing in map)
        NCNRNS = tuple(numpy.frombuffer(header_buf, dtype="int32")[:3])
        #4      MODE            Data type
        #                  0 = envelope stored as signed bytes (from
        #                      -128 lowest to 127 highest)
        #                  1 = Image     stored as Integer*2
        #                  2 = Image     stored as Reals
        #                  3 = Transform stored as Complex Integer*2
        #                  4 = Transform stored as Complex Reals
        #                  5 == 0	
        #
        #                  Note: Mode 2 is the normal mode used in
        #                        the CCP4 programs. Other modes than 2 and 0
        #                        may NOT WORK
        MODE = numpy.frombuffer(header_buf, dtype="int32")[3]
        dtype = ["i8", "int32", "float32", "cint32", "complex64", "i8"][MODE]
        if dtype_mode not in [0,2]:
            log_warning(logger, "WARNING: Map file data type \"MODE=%i\" may not work." % MODE)
        #24      NSYMBT          Number of bytes used for storing symmetry operators
        NSYMBT = numpy.frombuffer(header_buf, dtype="int32")[23]
        if NSYMBT > 0:
            log_warning(logger, "WARNING: Omitting symmetry operations in map file.")
            f.read(NSYMBT)
        # The remaining bytes are data
        data = f.read()
        data = numpy.frombuffer(data, dtype=dtype).reshape(NCNRNS)
    return data, dx
