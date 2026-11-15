# Contributing

The goal is to rehost the original NAC software while keeping its update
package intact. Work should remain reproducible with QEMU TCG and the pinned
tool versions used by the preparation scripts.

Useful next steps include integrating the verified Mesa software path with Qt Quick,
Winston output compatibility, persistence initialization and explicit stubs for
the vehicle services needed by the HMI. Record which behavior is observed and
which behavior is simulated.

Before submitting a change:

1. Run `python -m unittest discover -s tests -v` from the repository directory.
2. Run the relevant local firmware probe when changing boot or guest behavior.
3. Describe the tested firmware, command, result and remaining limitations.

Commit source, synthetic test fixtures and concise findings. Keep firmware,
keys, personal vehicle data, extracted binaries, dependency downloads, generated
images and raw logs outside commits. New binary formats should be handled with
bounds checks and a test for malformed input.
