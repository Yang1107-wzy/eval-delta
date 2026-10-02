# eval-delta: design

Compare evaluation runs by sample ID and catch metric regressions.

Architecture: pure analysis core plus argparse CLI. Python standard library only. File input is treated as untrusted data; no commands from input are executed. Stable JSON reports and documented exit codes make CI integration possible. Synthetic examples exercise both success and failure. Test behavior and failures before implementation.
