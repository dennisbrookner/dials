from __future__ import division

def open(filename, mode='a'):
  import h5py
  handle = h5py.File(filename, mode)
  if 'entry' in handle:
    entry = handle['entry']
    assert(entry.attrs['NX_class'] == 'NXentry')
  else:
    entry = handle.create_group('entry')
    entry.attrs['NX_class'] = 'NXentry'
  return entry

def load(filename):
  from dials.util.nexus import nx_diffraction, nx_mx
  entry = open(filename, "r")
  exp = nx_mx.load(entry)
  ref = nx_diffraction.load(entry)
  return exp, ref

def dump(experiments, reflections, filename):
  from dials.util.nexus import nx_diffraction, nx_mx
  entry = open(filename, "w")
  nx_mx.dump(entry, experiments)
  nx_diffraction.dump(entry, reflections)
