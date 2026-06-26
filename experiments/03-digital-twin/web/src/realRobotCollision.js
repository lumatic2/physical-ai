export const REAL_ROBOT_COLLISION_CONTRACTS = {
  "unitree-g1-v1": {
    id: "unitree-g1-v1",
    robot: "Unitree G1",
    source: "Browser MuJoCo G1 collision envelope mapped to a real-robot safety contract.",
    requiredTelemetry: [
      "imu.orientation",
      "imu.angular_velocity",
      "base.linear_acceleration",
      "joint.position",
      "joint.velocity",
      "joint.torque_or_current",
      "actuator.enabled_state",
      "operator.estop_state",
    ],
    requiredActuationGate: [
      "zero_velocity_command",
      "torque_disable_or_damping_mode",
      "hardware_estop_or_power_cut",
      "operator_reset_after_contact",
    ],
    stopCriteria: {
      maxBaseTiltRad: 0.75,
      maxBaseAccelerationMps2: 18,
      maxJointTorqueRatio: 0.85,
      maxUncommandedBaseDropM: 0.12,
      requireManualReset: true,
    },
    bodyZones: [
      {
        id: "pelvis",
        simGeoms: ["pelvis_floor_collision"],
        realEnvelope: "capsule around pelvis shell",
        protectiveAction: "stop locomotion and enter damping/hold state before body scrape continues",
      },
      {
        id: "torso",
        simGeoms: ["torso_floor_collision"],
        realEnvelope: "capsule along torso trunk",
        protectiveAction: "disable gait command and require operator inspection",
      },
      {
        id: "head",
        simGeoms: ["head_floor_collision"],
        realEnvelope: "sphere around head/sensor pod",
        protectiveAction: "hard stop; sensor pod contact is not recoverable in autonomous mode",
      },
      {
        id: "feet",
        simGeoms: ["left_foot", "right_foot"],
        realEnvelope: "sole contact patches",
        plannedContact: true,
        protectiveAction: "allowed planned ground contact; monitor slip and impulse only",
      },
    ],
    claimBoundary:
      "Real-robot collision readiness contract only. It is not armed without a hardware telemetry bridge, actuator disable path, and operator e-stop evidence.",
  },
};

export function summarizeRealRobotCollisionReadiness(context = {}) {
  const contract = REAL_ROBOT_COLLISION_CONTRACTS[context.contractId || "unitree-g1-v1"];
  const sceneText = `${context.experimentName || ""} ${context.scene || ""} ${context.title || ""}`;
  const applies = /g1/i.test(sceneText);
  const modelGeoms = Array.isArray(context.modelGeoms) ? context.modelGeoms : [];
  const telemetryBridgePresent = Boolean(context.telemetryBridgePresent);
  const actuationGatePresent = Boolean(context.actuationGatePresent);
  const estopEvidencePresent = Boolean(context.estopEvidencePresent);
  const bodyZones = contract.bodyZones.map((zone) => {
    const geoms = zone.simGeoms.map((name) => modelGeoms.find((geom) => geom.name === name) || { name, missing: true });
    return {
      ...zone,
      geoms,
      present: geoms.every((geom) => !geom.missing),
      contactEligible: zone.plannedContact
        ? geoms.every((geom) => !geom.missing)
        : geoms.every((geom) => !geom.missing && Number(geom.contype) > 0 && Number(geom.conaffinity) > 0),
    };
  });
  const simEnvelopeCoveragePass = applies ? bodyZones.every((zone) => zone.present && zone.contactEligible) : true;
  const hardwareReady = telemetryBridgePresent && actuationGatePresent && estopEvidencePresent;
  return {
    id: contract.id,
    robot: contract.robot,
    applies,
    source: contract.source,
    bodyZones,
    requiredTelemetry: contract.requiredTelemetry,
    requiredActuationGate: contract.requiredActuationGate,
    stopCriteria: contract.stopCriteria,
    simEnvelopeCoveragePass,
    telemetryBridgePresent,
    actuationGatePresent,
    estopEvidencePresent,
    hardwareReady,
    realRobotCollisionArmed: hardwareReady,
    state: hardwareReady ? "hardware-ready-contract" : "sim-envelope-ready-hardware-bridge-missing",
    pass: Boolean(simEnvelopeCoveragePass && !hardwareReady),
    claimBoundary: contract.claimBoundary,
  };
}
