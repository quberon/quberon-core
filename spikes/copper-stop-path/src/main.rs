#![allow(deprecated)]

use cu29::bincode::{Decode, Encode, config::standard, encode_to_vec};
use cu29::prelude::*;
use cu29_export::{copperlists_reader, keyframes_reader};
use cu29_unifiedlog::memmap::{MmapSectionStorage, MmapUnifiedLoggerWrite};
use cu29_unifiedlog::{UnifiedLogger, UnifiedLoggerBuilder, UnifiedLoggerIOReader};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};

#[derive(Default, Debug, Clone, PartialEq, Encode, Decode, Serialize, Deserialize, Reflect)]
struct Intervention {
    command: String,
    sequence: u64,
}

#[derive(Default, Debug, Clone, PartialEq, Encode, Decode, Serialize, Deserialize, Reflect)]
struct AuthorizationDecision {
    command: String,
    sequence: u64,
    authorized: bool,
}

#[derive(Reflect)]
struct InterventionSource;

impl Freezable for InterventionSource {}

impl CuSrcTask for InterventionSource {
    type Resources<'r> = ();
    type Output<'m> = output_msg!(Intervention);

    fn new(_config: Option<&ComponentConfig>, _resources: Self::Resources<'_>) -> CuResult<Self> {
        Ok(Self)
    }

    fn process(&mut self, _ctx: &CuContext, output: &mut Self::Output<'_>) -> CuResult<()> {
        output.set_payload(Intervention {
            command: "STOP".to_owned(),
            sequence: 1,
        });
        Ok(())
    }
}

#[derive(Reflect)]
struct Authorization;

impl Freezable for Authorization {}

impl CuTask for Authorization {
    type Resources<'r> = ();
    type Input<'m> = input_msg!(Intervention);
    type Output<'m> = output_msg!(AuthorizationDecision);

    fn new(_config: Option<&ComponentConfig>, _resources: Self::Resources<'_>) -> CuResult<Self> {
        Ok(Self)
    }

    fn process(
        &mut self,
        _ctx: &CuContext,
        input: &Self::Input<'_>,
        output: &mut Self::Output<'_>,
    ) -> CuResult<()> {
        match input.payload() {
            Some(intervention) => output.set_payload(AuthorizationDecision {
                command: intervention.command.clone(),
                sequence: intervention.sequence,
                authorized: intervention.command == "STOP",
            }),
            None => output.clear_payload(),
        }
        Ok(())
    }
}

#[derive(Reflect)]
struct SimulatedActuator;

impl Freezable for SimulatedActuator {}

impl CuSinkTask for SimulatedActuator {
    type Resources<'r> = ();
    type Input<'m> = input_msg!(AuthorizationDecision);

    fn new(_config: Option<&ComponentConfig>, _resources: Self::Resources<'_>) -> CuResult<Self> {
        Ok(Self)
    }

    fn process(&mut self, _ctx: &CuContext, input: &Self::Input<'_>) -> CuResult<()> {
        let decision = input
            .payload()
            .ok_or_else(|| CuError::from("actuator received no authorization decision"))?;
        if decision.command != "STOP" || !decision.authorized {
            return Err(CuError::from(
                "actuator rejected non-STOP or unauthorized command",
            ));
        }
        Ok(())
    }
}

#[copper_runtime(config = "copper.ron", sim_mode = true)]
struct StopPathApp {}

fn logger(path: &Path) -> CuResult<Arc<Mutex<MmapUnifiedLoggerWrite>>> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)
            .map_err(|error| CuError::new_with_cause("create evidence directory failed", error))?;
    }
    let UnifiedLogger::Write(writer) = UnifiedLoggerBuilder::new()
        .write(true)
        .create(true)
        .preallocated_size(16 * 1024 * 1024)
        .file_base_name(path)
        .build()
        .map_err(|error| CuError::new_with_cause("logger initialization failed", error))?
    else {
        return Err(CuError::from("logger builder did not return a writer"));
    };
    Ok(Arc::new(Mutex::new(writer)))
}

fn read_copperlist(path: &Path) -> CuResult<CopperList<default::CuStampedDataSet>> {
    let UnifiedLogger::Read(reader) = UnifiedLoggerBuilder::new()
        .file_base_name(path)
        .build()
        .map_err(|error| CuError::new_with_cause("open Copper log failed", error))?
    else {
        return Err(CuError::from("logger builder did not return a reader"));
    };
    let mut stream = UnifiedLoggerIOReader::new(reader, UnifiedLogType::CopperList);
    copperlists_reader::<default::CuStampedDataSet>(&mut stream)
        .next()
        .ok_or_else(|| CuError::from("Copper log contained no task outputs"))
}

fn read_keyframe(path: &Path) -> CuResult<KeyFrame> {
    let UnifiedLogger::Read(reader) = UnifiedLoggerBuilder::new()
        .file_base_name(path)
        .build()
        .map_err(|error| CuError::new_with_cause("open keyframe log failed", error))?
    else {
        return Err(CuError::from("logger builder did not return a reader"));
    };
    let mut stream = UnifiedLoggerIOReader::new(reader, UnifiedLogType::FrozenTasks);
    keyframes_reader(&mut stream)
        .next()
        .ok_or_else(|| CuError::from("Copper log contained no keyframe"))
}

fn encode<T: Encode>(value: &T) -> CuResult<Vec<u8>> {
    encode_to_vec(value, standard())
        .map_err(|error| CuError::new_with_cause("encode deterministic evidence failed", error))
}

fn record(path: &Path) -> CuResult<(CopperList<default::CuStampedDataSet>, KeyFrame)> {
    let (clock, _clock_mock) = RobotClock::mock();
    let mut runtime = |_step: default::SimStep<'_>| SimOverride::ExecuteByRuntime;
    let mut app = StopPathApp::builder()
        .with_clock(clock)
        .with_logger::<MmapSectionStorage, MmapUnifiedLoggerWrite>(logger(path)?)
        .with_sim_callback(&mut runtime)
        .build()?
        .into_inner();
    app.start_all_tasks(&mut runtime)?;
    app.run_one_iteration(&mut runtime)?;
    app.stop_all_tasks(&mut runtime)?;
    drop(app);
    Ok((read_copperlist(path)?, read_keyframe(path)?))
}

fn replay(
    path: &Path,
    recorded: &CopperList<default::CuStampedDataSet>,
    keyframe: &KeyFrame,
) -> CuResult<(CopperList<default::CuStampedDataSet>, KeyFrame)> {
    let (clock, clock_mock) = RobotClock::mock();
    let mut runtime = |_step: default::SimStep<'_>| SimOverride::ExecuteByRuntime;
    let mut app = StopPathApp::builder()
        .with_clock(clock)
        .with_logger::<MmapSectionStorage, MmapUnifiedLoggerWrite>(logger(path)?)
        .with_sim_callback(&mut runtime)
        .build()?
        .into_inner();
    app.start_all_tasks(&mut runtime)?;
    app.replay_recorded_copperlist(&clock_mock, recorded, Some(keyframe))?;
    app.stop_all_tasks(&mut runtime)?;
    drop(app);
    Ok((read_copperlist(path)?, read_keyframe(path)?))
}

fn write_evidence(directory: &Path) -> CuResult<()> {
    fs::create_dir_all(directory)
        .map_err(|error| CuError::new_with_cause("create evidence directory failed", error))?;
    let recorded_log = directory.join("original.copper");
    let replayed_log = directory.join("replay.copper");
    let (recorded, recorded_keyframe) = record(&recorded_log)?;
    let (replayed, replayed_keyframe) = replay(&replayed_log, &recorded, &recorded_keyframe)?;
    let recorded_bytes = encode(&recorded)?;
    let replayed_bytes = encode(&replayed)?;
    fs::write(directory.join("original-task-outputs.bin"), &recorded_bytes)
        .map_err(|error| CuError::new_with_cause("write original outputs failed", error))?;
    fs::write(directory.join("replay-task-outputs.bin"), &replayed_bytes)
        .map_err(|error| CuError::new_with_cause("write replay outputs failed", error))?;
    if recorded_bytes != replayed_bytes
        || encode(&recorded_keyframe)? != encode(&replayed_keyframe)?
    {
        return Err(CuError::from("record/replay output mismatch"));
    }
    let source = recorded
        .msgs
        .0
        .0
        .payload()
        .ok_or_else(|| CuError::from("missing source output"))?;
    let authorization = recorded
        .msgs
        .0
        .1
        .payload()
        .ok_or_else(|| CuError::from("missing authorization output"))?;
    if source.command != "STOP" || authorization.command != "STOP" || !authorization.authorized {
        return Err(CuError::from(
            "recorded run did not contain an authorized STOP",
        ));
    }
    fs::write(
        directory.join("comparison.txt"),
        format!(
            "command=STOP\nsequence={}\nauthorized=true\noriginal_task_outputs_bytes={}\nreplay_task_outputs_bytes={}\nbyte_identical=true\nkeyframe_byte_identical=true\n",
            source.sequence,
            recorded_bytes.len(),
            replayed_bytes.len()
        ),
    )
    .map_err(|error| CuError::new_with_cause("write comparison failed", error))?;
    println!("STOP_RECORDED sequence={}", source.sequence);
    println!("TASK_OUTPUTS_BYTE_IDENTICAL bytes={}", recorded_bytes.len());
    println!("KEYFRAME_BYTE_IDENTICAL");
    Ok(())
}

fn main() -> CuResult<()> {
    let directory = std::env::args_os()
        .nth(1)
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("evidence/generated"));
    write_evidence(&directory)
}
