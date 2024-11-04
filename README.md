# Large Scale Digital Design Dataset

This project aims to build the largest collection of digital hardware design sources. This includes collecting public sources, writing scripts for automated fetching, preprocessing design sources into a common structure, checking for HDL syntax correctness, and verifying synthesizability. This project also aims to provide a generic extendable API for wiring custom flows for user-defined feature extraction and running external tools to generate more associated design data. The hope is that the presented dataset will be productive for EDA research, including benchmarking and deep learning research.

This project is a spin-off of an internal research project under the Hardware Security and Trust (HST) group in CIPHER lab at Georgia Tech Research Institute (GTRI).

## Contact

This work is pursued by Stefan Abi-Karam ([Stefan.Abi-Karam@gtri.gatech.edu](mailto:Stefan.Abi-Karam@gtri.gatech.edu), [stefanabikaram@gatech.edu](mailto:stefanabikaram@gatech.edu)). Please feel free to reach out for any inquiries.

## Status

✅: Completed, 🏗️: Actively In-Progress, 〰️: Planned

### Dataset Sources

- ✅ OS - OpenCores / FreeCores (hand-curated subset, ~126 designs)
- 〰️ OS - BlackParrot
- 〰️ OS - MemPool
- 〰️ OS - NVDLA
- 〰️ OS - CVA6
- 〰️ OS - Vortex GPGPU
- 🏗️ OS - FPNew
- 🏗️ OS - SERV Core
- 〰️ OS - OpenTitan
- 🏗️ OS - FuseSoC Core Library
- 🏗️ OS - secworks Core Library
- 〰️ OS - MLBlocks
- 〰️ OS - PULP Cores and Libraries
- 〰️ OS - GRLIB IP Library
- 🏗️ OS - tangxifan/micro\_benchmark
- 〰️ OS - DeepBenchVerilog
- 〰️ OS - UT-LCA/tpu\_like\_design
- 〰️ OS - UT-LCA/tpu\_v2
- 〰️ OS - UT-LCA/brainwave-like-design
- 〰️ OS - mongrelgem/Verilog-Adder
- ✅ Bench - HW2VEC
- ✅ Bench - OpenPiton Design Benchmark
- ✅ Bench - Verilog to Routing (VTR)
- ✅ Bench - Koios 2.0
- 🏗️ Bench - Titan 2.0
- 🏗️ Bench - MCNC 20
- ✅ Bench - ISCAS 85
- ✅ Bench - ISCAS 89
- ✅ Bench - LGSynth 89
- 🏗️ Bench - LGSynth 91
- 🏗️ Bench - IWLS 93
- 🏗️ Bench - I99T (ITC 99 subset)
- 🏗️ Bench - IWLS 2005: Faraday Subset
- 🏗️ Bench - IWLS 2005: Gaisler Subset
- ✅ Bench - EPFL Combinational Benchmark
- 🏗️ Bench - HDLBits / VerilogEval Subset
- 🏗️ HLS - PolyBench
- 🏗️ HLS - Machsuite
- 🏗️ HLS - Rosetta
- 🏗️ HLS - CHStone
- 〰️ HLS - Rodina
- 〰️ HLS - Parallel Programming For FPGAs
- 〰️ HLS - Xilinx/Vitis-HLS-Introductory-Examples
- 〰️ Exp - Regex State Machines
- 〰️ Exp - Scraped Efabless Submissions
- 〰️ DSL / Arch - PGRA
- 〰️ DSL / Arch - OpenFPGA
- 〰️ DSL / Arch - FloPoCo

OS: Open Source, Bench: Benchmark, HLS: High-Level Synthesis, Exp: Experiment, DSL / Arch: Domain Specific Language and Architecture Generators

Note 1: Since we define Verilog as our based HDL, we must translate some sources from formats like VHDL or BLIF into Verilog. These only apply to a few cases so far such as Titan benchmarks and the GRLIB IP library.

Note 2: For HLS-based sources, we can use different HLS tools for different versions of the source. To begin with, we will use Vitis HLS. Other HLS tools include Intel HLS Compiler, Microchip's SmartHLS, Bambu, and Dynamatic.

### Flows

- ✅ Verible - AST / CST
- ✅ Yosys - Module Listing
- 🏗️ Yosys - Module Hierarchy
- ✅ Yosys - Generic Synthesis / AIG (using `synth` + `aigmap`)
- 🏗️ Yosys - Xilinx Synthesis + Techmap
- 🏗️ ISE - Synth + PnR
- 〰️ Vivado - Synth + PnR
- 〰️ Quartus - Synth + PnR
- 〰️ OpenROAD

There is an explicit focus on FPGA tools as an initial priority since the active research this project is part of is focused on EDA flows for FPGAs.