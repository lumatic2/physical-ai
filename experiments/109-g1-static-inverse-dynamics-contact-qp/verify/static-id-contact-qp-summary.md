# G1 Static Inverse-Dynamics Contact QP Summary

| Pose | Verdict | Drop | Knee | Hip | CoM margin | Base residual | Lower tau | Normal | Friction ratio |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| exp108-best-no-fall | BASE_DYNAMICS_RESIDUAL_HIGH | 0.075m | 0.382 | 0.210 | 0.0837m | 94228.45 | 4996.91 | 327.1N | 0.000 |
| exp29-visible-min | STATIC_ID_QP_PLAUSIBLE | 0.080m | 0.600 | 0.350 | 0.0718m | 5.14 | 25.36 | 327.2N | 0.012 |
| visible-soft-pose | BASE_DYNAMICS_RESIDUAL_HIGH | 0.085m | 0.500 | 0.300 | 0.0693m | 53268.00 | 3487.92 | 327.1N | 0.000 |
| visible-full-pose | STATIC_ID_QP_PLAUSIBLE | 0.090m | 0.640 | 0.380 | 0.0674m | 4.28 | 25.75 | 327.2N | 0.010 |

Best static pose: {'spec': {'name': 'visible-full-pose', 'drop': 0.09, 'knee': 0.64, 'hip': 0.38, 'ankle': 0.28}, 'support': {'support_margin': 0.06743510572093545, 'com_support_margin': 0.06743510572093545, 'com_xy': [0.059852000701064036, 8.226090168117387e-05]}, 'qp': {'success': True, 'status': 'Optimization terminated successfully', 'force_solution': {'left_fx': 1.3365669147758767, 'left_fy': -0.0887459260145139, 'left_fz': 163.7032306762101, 'right_fx': 1.3355295944894812, 'right_fy': 0.09164250319773926, 'right_fz': 163.53063427588864, 'total_normal': 327.23386495209877, 'max_friction_ratio': 0.010232563683570112}, 'base_residual_l2': 5.04850379764284, 'base_residual_linf': 4.280482398928594, 'tau_linf': 25.74767405047201, 'tau_l2': 36.63285883483145, 'lower_tau_linf': 25.74767405047201, 'qfrc_required_linf': 327.07660302000005, 'qfrc_required_base_linf': 327.07660302000005, 'qfrc_required_act_linf': 8.5597046032105, 'objective': 2587.9002457257056}, 'verdict': 'STATIC_ID_QP_PLAUSIBLE'}

This is a static inverse-dynamics feasibility diagnostic, not a native rollout pass.
