import os

this_dir = os.path.dirname(os.path.realpath(__file__))

examples = [
    {
        "dir": this_dir + "/examples/configfile/particle_sphere",
        "cmd": "condor",
    },
    {
        "dir": this_dir + "/examples/configfile/particle_spheroid",
        "cmd": "condor",
    },
    {
        "dir": this_dir + "/examples/configfile/particle_map",
        "cmd": "condor",
    },
    {
        "dir": this_dir + "/examples/configfile/particle_atoms",
        "cmd": "condor",
    },
    {
        "dir": this_dir + "/examples/configfile/custom_map",
        "cmd": "condor",
    },
    {
        "dir": this_dir + "/examples/scripts/custom_map",
        "cmd": "python example.py",
    },
    {
        "dir": this_dir + "/examples/scripts/emd_fetch",
        "cmd": "python example.py",
    },
    {
        "dir": this_dir + "/examples/scripts/particle_models",
        "cmd": "python example.py",
    },
    {
        "dir": this_dir + "/examples/scripts/rotations",
        "cmd": "python example.py",
    },
    {
        "dir": this_dir + "/examples/scripts/simple",
        "cmd": "python example.py",
    },
    {
        "dir": this_dir + "/examples/scripts/pdb_fetch",
        "cmd": "python example.py",
    },

]

    
for i,e in enumerate(examples):
    print "Starting example %i" % i
    cmd = "cd %s; %s" % (e["dir"],e["cmd"])
    print cmd
    os.system(cmd)
    print "Exiting example %i" % i
