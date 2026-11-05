# quberon-evidence-bundle (standalone crate)

Simulation-only evidence bundle builder/validator. See SPEC.md.
Not a member of the root workspace (its Cargo.toml declares its own
`[workspace]`); the root workspace, MSRV, and secure-core crate are
untouched.

  cargo test --offline --manifest-path crates/quberon-evidence-bundle/Cargo.toml
  cargo run --offline --manifest-path crates/quberon-evidence-bundle/Cargo.toml -- validate <bundle.qeb>

For day-to-day third-party verification prefer the dependency-free
Python verifier in tools/quberon-verify/ (stdlib only, offline).
