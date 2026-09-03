"""B4 baseline — DESCRIPTIVE_REGRESSION_EVIDENCE (B3 main bf71b21d).

Captured at B3 main BEFORE B4 via the clean G2C production entry point
(python subprocess in a clean git worktree at bf71b21d). Expanded metric
matrix (Correction B): operating, tax/CFADS, Senior, DSCR, binding
constraint, G2A capacities, manual construction/VAT input guards, derived
construction-financing authority, SHL, distributions, sponsor receipts,
plus operating and construction period-vector digests. Manual fields are
zero dual-authority guards; they are not economic financing outputs. The
derived layer is captured directly from
``financing_result.construction_financing`` (``None`` means not applicable).
Regression evidence ONLY: never read by runtime or financial code; no
engine value was fitted to match it.
Provenance: git worktree @ bf71b21dfe1130a100454bbc5d6faa2c9db4e549 (base SHA).

PROVENANCE STATUS (R.11 restoration):
  Scalars — ALL scalar values in this file are the actual bf71b21d originals,
    restored from the N.2 ULP NOTE where they had drifted.
  Period-vector hashes (Solar, Wind) — unaffected by N.2; retained as captured
    at bf71b21d.
  Period-vector hashes (Oborovo, TUHO operating schedules) — were overwritten by
    N.2 ULP cascade when originally captured; the true bf71b21d originals are
    unavailable without re-running the model at bf71b21d. Stored as
    'UNAVAILABLE_AT_BF71'. No active test reads these keys.
  Period-vector hashes (Oborovo, TUHO construction schedules) — were captured at
    current production, not at a clean bf71b21d worktree; unavailable. Stored as
    'UNAVAILABLE_AT_BF71'. No active test reads these keys.
  Current-production values and hashes — live only in b4a_current_production_baseline.py.

N.2 ULP NOTE: The N.2 distribution-accounting gating commit introduced ≤1-ULP
floating-point cascade in Solar, Wind, Oborovo, and TUHO computed summations.
The economic conclusions (DSCR, senior debt size, returns) are unchanged; only
12th-decimal-place arithmetic artefacts differ. Scalar values HERE are bf71b21d
originals. Post-N.2 values live in b4a_current_production_baseline.py.
Affected fields and their post-N.2 counterparts (for cross-reference):
  Solar:   opex   bf71=9233.000523588735  → post-N.2 9233.000523588737
           cash_tax  bf71=9612.66059784277  → post-N.2 9612.660597842772
           base_cfads bf71=75568.8876901546 → post-N.2 75568.88769015462
           min_dscr bf71=1.1029022100705497 → post-N.2 1.10290221007055
           avg_dscr bf71=1.3460458391604466 → post-N.2 1.346045839160447
           shl_terminal bf71=6629.459631504193 → post-N.2 6629.45963150419
           distributions bf71=5002.162578513825 → post-N.2 5002.162578513828
           sponsor_receipts bf71=14904.066887275436 → post-N.2 14904.06688727544
           senior_principal bf71=24750.000000000007 → post-N.2 24750.0
  Wind:    revenue bf71=213093.25362988273 → post-N.2 213093.2536298828
           opex bf71=17617.771476803053 → post-N.2 17617.771476803056
           cash_tax bf71=32612.879216704838 → post-N.2 32612.879216704834
           senior_principal bf71=32250.0 → post-N.2 32249.999999999996
           senior_ds bf71=42650.79738447129 → post-N.2 42650.79738447128
  Oborovo: revenue bf71=237686.92241665165 → post-N.2 237686.92241665168
           opex bf71=55782.95083863444 → post-N.2 55782.950838634424
           ebitda bf71=181903.97157801723 → post-N.2 181903.97157801728
           senior_ds bf71=62985.39289808685 → post-N.2 62985.39289808684
           avg_dscr bf71=1.2425786312134315 → post-N.2 1.2425786312134317
  TUHO:    revenue bf71=423762.0018183332 → post-N.2 423762.00181833334
           ebitda bf71=338358.5508177341 → post-N.2 338358.55081773404
           senior_interest bf71=23046.055518013454 → post-N.2 23046.05551801346
           senior_principal bf71=43789.92111682597 → post-N.2 43789.92111682598
           senior_ds bf71=66835.97663483942 → post-N.2 66835.97663483946
           min_dscr bf71=1.398269618156276 → post-N.2 1.3982696181562762
           avg_dscr bf71=1.5301592230503733 → post-N.2 1.5301592230503727
           construction_senior_idc_raw bf71=1769.3542393177283 → post-N.2 1769.3542393177286
           construction_senior_idc_capitalized bf71=1552.2292137801358 → post-N.2 1552.229213780136
"""

_B3_MAIN_BASELINE = {
    'Solar': {
        'revenue': 94414.54881158611,
        'opex': 9233.000523588735,  # bf71b21d original (post-N.2: 9233.000523588737)
        'ebitda': 85181.54828799739,
        'cash_tax': 9612.66059784277,  # bf71b21d original (post-N.2: 9612.660597842772)
        'base_cfads': 75568.8876901546,  # bf71b21d original (post-N.2: 75568.88769015462)
        'bank_cfads': 70815.23670051334,
        'senior_debt_size': 24750.0,
        'senior_interest': 10552.125188205955,
        'senior_principal': 24750.000000000007,  # bf71b21d original (post-N.2: 24750.0)
        'senior_ds': 35302.12518820596,
        'senior_terminal': 0.0,
        'min_dscr': 1.1029022100705497,  # bf71b21d original (post-N.2: 1.10290221007055)
        'avg_dscr': 1.3460458391604466,  # bf71b21d original (post-N.2: 1.346045839160447)
        'binding_constraint': 'GEARING',
        'dscr_debt_capacity': 28458.117382991935,
        'gearing_debt_capacity': 24750.0,
        'total_project_uses': 33000.0,
        'manual_capex_idc_input_keur': 0.0,
        'manual_commitment_fee_input_keur': 0.0,
        'manual_structuring_fee_input_keur': 0.0,
        'manual_vat_costs_input_keur': 0.0,
        'manual_vat_idc_input_keur': 0.0,
        'manual_vat_fee_input_keur': 0.0,
        'construction_financing': None,
        'shl_first_op_opening': 7750.0,
        'shl_total_interest': 10112.114041746758,
        'shl_total_principal': 1410.1566717193427,
        'shl_terminal': 6629.459631504193,  # bf71b21d original (post-N.2: 6629.45963150419)
        'distributions': 5002.162578513825,  # bf71b21d original (post-N.2: 5002.162578513828)
        'sponsor_receipts': 14904.066887275436,  # bf71b21d original (post-N.2: 14904.06688727544)
        "period_vectors": {
            'senior_interest': '13de78a4daa532b57c368d07057e276927a547d48deb87bb94fa7cb9b2540871',
            'senior_principal': 'eff6076ae69e3dc9c5eb009939756b3e7e3cde2db2e7b0d6da49e46b591ba31a',
            'senior_ds': '17f67c9383e5d0c76303118eb0ee012b9378ee810cb8284d568964a2e807208d',
            'senior_closing': 'fb1712943ae276616603310634e4d0202cc4c64215c8d3d9a9275899d6c541e9',
            'shl_interest': '1009c510ae2927f9ab31183d67d5c0d85ddfb5d8c533ce8b98fcf173e257662b',
            'shl_principal': '19592c4a8c2ba8b5eb9eaf61b0e5f648e241d9bf67d9f20e9c83adef373b8d15',
            'shl_closing': '807b239c903a0dce7095fd725de8c97d2fdd9e92b9ec5a0eb512627b4d2bc223',
        },
    },
    'Wind': {
        'revenue': 213093.25362988273,  # bf71b21d original (post-N.2: 213093.2536298828)
        'opex': 17617.771476803053,  # bf71b21d original (post-N.2: 17617.771476803056)
        'ebitda': 195475.48215307965,
        'cash_tax': 32612.879216704838,  # bf71b21d original (post-N.2: 32612.879216704834)
        'base_cfads': 162862.60293637484,
        'bank_cfads': 146880.60891413366,
        'senior_debt_size': 32250.0,
        'senior_interest': 10400.797384471289,
        'senior_principal': 32250.0,  # bf71b21d original (post-N.2: 32249.999999999996)
        'senior_ds': 42650.79738447129,  # bf71b21d original (post-N.2: 42650.79738447128)
        'senior_terminal': 0.0,
        'min_dscr': 1.2766883984398625,
        'avg_dscr': 4.291962244065097,
        'binding_constraint': 'GEARING',
        'dscr_debt_capacity': 45842.05065359109,
        'gearing_debt_capacity': 32250.0,
        'total_project_uses': 43000.0,
        'manual_capex_idc_input_keur': 0.0,
        'manual_commitment_fee_input_keur': 0.0,
        'manual_structuring_fee_input_keur': 0.0,
        'manual_vat_costs_input_keur': 0.0,
        'manual_vat_idc_input_keur': 0.0,
        'manual_vat_fee_input_keur': 0.0,
        'construction_financing': None,
        'shl_first_op_opening': 10250.0,
        'shl_total_interest': 13120.0,
        'shl_total_principal': 3861.8674582381464,
        'shl_terminal': 6388.132541761854,
        'distributions': 10506.513025614555,
        'sponsor_receipts': 21942.7997169778,
        "period_vectors": {
            'senior_interest': 'b1302c5b48f7ea29d0ecf1209a2f720915fc999aa59d3ab232474f616063038f',
            'senior_principal': '337cde694ff84065c2de13648b66328dcad9b70efe425bdb3b19a2d193193bb9',
            'senior_ds': '38cccafd335787352fbf72180cede4793a600a87ea8fc72174c05852a2c4131b',
            'senior_closing': '0c6ad39bffece08ce54966a8bb72d6624f2b81f7da94763c81256867ba96f91c',
            'shl_interest': 'aa8a785e205f84f705e3e0b76ac56ca4189d58d799fbc862a85c6e6eaa567c51',
            'shl_principal': '3e0d46e2e5cc378acf6f044d9e2209e6f60b138accca15b4475343f162b690a9',
            'shl_closing': '6bc84bd96288ea15b8e5b8c9f3edb860f45212f8fdc51548f426ef75b6d0bcba',
        },
    },
    'Oborovo': {
        'revenue': 237686.92241665165,  # bf71b21d original (post-N.2: 237686.92241665168)
        'opex': 55782.95083863444,  # bf71b21d original (post-N.2: 55782.950838634424)
        'ebitda': 181903.97157801723,  # bf71b21d original (post-N.2: 181903.97157801728)
        'cash_tax': 10437.90476711545,
        'base_cfads': 171466.06681090177,
        'bank_cfads': 141761.6415624344,
        'senior_debt_size': 42852.302723344226,
        'senior_interest': 20133.090174742636,
        'senior_principal': 42852.30272334422,
        'senior_ds': 62985.39289808685,  # bf71b21d original (post-N.2: 62985.39289808684)
        'senior_terminal': 0.0,
        'min_dscr': 1.0681918096431542,
        'avg_dscr': 1.2425786312134315,  # bf71b21d original (post-N.2: 1.2425786312134317)
        'binding_constraint': 'DSCR',
        'dscr_debt_capacity': 42852.302723344226,
        'gearing_debt_capacity': 43618.91701149782,  # bf71b21d original (post-N.2: 43618.91701149781)
        'total_project_uses': 57973.042280034315,  # bf71b21d original (post-N.2: 57973.04228003431)
        'manual_capex_idc_input_keur': 0.0,
        'manual_commitment_fee_input_keur': 0.0,
        'manual_structuring_fee_input_keur': 0.0,
        'manual_vat_costs_input_keur': 0.0,
        'manual_vat_idc_input_keur': 0.0,
        'manual_vat_fee_input_keur': 0.0,
        'construction_financing': {
            'authority': 'PR9_TYPED_CONSTRUCTION_FINANCING_IDC_AUTHORITY',
            'construction_senior_idc_raw': 1086.0191130858313,  # bf71b21d original (post-N.2: 1086.0191130858318)
            'construction_senior_idc_capitalized': 1086.0191130858311,  # bf71b21d original (post-N.2: 1086.0191130858316)
            'construction_senior_commitment_fee': 188.56540868282153,  # bf71b21d original (post-N.2: 188.56540868282144)
            'construction_structuring_fee': 477.302687,
            'construction_total_capitalized_financing': 1973.9567800340324,  # bf71b21d original (post-N.2: 1973.9567800340328)
            'vat_idc': 208.44761845456716,  # bf71b21d original (post-N.2: 208.4476184545672)
            'vat_commitment_fee': 13.6219528108125,  # bf71b21d original (post-N.2: 13.621952810812502)
            'vat_effective_commitment': 4877.989945,
            'vat_peak_requirement': 4877.989945,
            'vat_commitment_mode': 'DERIVED_PEAK_REQUIREMENT',
            'vat_authority': 'TYPED_CONSTRUCTION_VAT_FACILITY_AUTHORITY',
            'final_total_project_uses': 57973.042280034315,  # bf71b21d original (post-N.2: 57973.04228003431)
            'final_senior_commitment': 42852.302723344226,
            'outer_iterations': 9,
            'stage_b2_iterations': 7,
            'outer_residual': 1.3857516023563221e-08,
            'final_verification_outer_residual': 3.490185918053612e-10,
            'hard_project_capex': 55999.0855,  # bf71b21d original (post-N.2: 55999.085499999994)
            'explicit_financing_cost_uses': 1973.9567800343161,  # bf71b21d original (post-N.2: 1973.9567800343166)
            'reserve_account_funding': 0.0,
            'other_explicit_project_uses': 0.0,
            'total_project_uses': 57973.042280034315,  # bf71b21d original (post-N.2: 57973.04228003431)
            'period_vectors': {
                # bf71b21d originals unavailable (not captured at a clean bf71b21d worktree)
                'senior_idc_accrual': 'UNAVAILABLE_AT_BF71',
                'senior_idc_capitalized_uses': 'UNAVAILABLE_AT_BF71',
                'senior_commitment_fee_accrual': 'UNAVAILABLE_AT_BF71',
                'structuring_fee': 'UNAVAILABLE_AT_BF71',
                'vat_payable': 'UNAVAILABLE_AT_BF71',
                'vat_requirement': 'UNAVAILABLE_AT_BF71',
                'vat_drawn': 'UNAVAILABLE_AT_BF71',
                'vat_undrawn': 'UNAVAILABLE_AT_BF71',
            },
        },
        'shl_first_op_opening': 15790.398721217909,  # bf71b21d original (post-N.2: 15790.398721217902)
        'shl_total_interest': 32103.921759523444,  # bf71b21d original (post-N.2: 32103.921759523422)
        'shl_total_principal': 26713.379909759595,  # bf71b21d original (post-N.2: 26713.379909759584)
        'shl_terminal': 0.0,
        'distributions': 61689.90265451222,
        'sponsor_receipts': 108480.6739128149,
        "period_vectors": {
            # bf71b21d originals unavailable (N.2 ULP cascade overwrote operating
            # schedule hashes before capture; re-running at bf71b21d required)
            'senior_interest': 'UNAVAILABLE_AT_BF71',
            'senior_principal': 'UNAVAILABLE_AT_BF71',
            'senior_ds': 'UNAVAILABLE_AT_BF71',
            'senior_closing': 'UNAVAILABLE_AT_BF71',
            'shl_interest': 'UNAVAILABLE_AT_BF71',
            'shl_principal': 'UNAVAILABLE_AT_BF71',
            'shl_closing': 'UNAVAILABLE_AT_BF71',
        },
    },
    'TUHO': {
        'revenue': 423762.0018183332,  # bf71b21d original (post-N.2: 423762.00181833334)
        'opex': 85403.45100059909,
        'ebitda': 338358.5508177341,  # bf71b21d original (post-N.2: 338358.55081773404)
        'cash_tax': 38915.55406411077,
        'base_cfads': 299442.99675362336,
        'bank_cfads': 196285.59264084484,
        'senior_debt_size': 43789.92111682598,
        'senior_interest': 23046.055518013454,  # bf71b21d original (post-N.2: 23046.05551801346)
        'senior_principal': 43789.92111682597,  # bf71b21d original (post-N.2: 43789.92111682598)
        'senior_ds': 66835.97663483942,  # bf71b21d original (post-N.2: 66835.97663483946)
        'senior_terminal': 0.0,
        'min_dscr': 1.398269618156276,  # bf71b21d original (post-N.2: 1.3982696181562762)
        'avg_dscr': 1.5301592230503733,  # bf71b21d original (post-N.2: 1.5301592230503727)
        'binding_constraint': 'DSCR',
        'dscr_debt_capacity': 43789.92111682598,
        'gearing_debt_capacity': 58424.82386508634,
        'total_project_uses': 73031.02983135793,
        'manual_capex_idc_input_keur': 0.0,
        'manual_commitment_fee_input_keur': 0.0,
        'manual_structuring_fee_input_keur': 0.0,
        'manual_vat_costs_input_keur': 0.0,
        'manual_vat_idc_input_keur': 0.0,
        'manual_vat_fee_input_keur': 0.0,
        'construction_financing': {
            'authority': 'PR9_TYPED_CONSTRUCTION_FINANCING_IDC_AUTHORITY',
            'construction_senior_idc_raw': 1769.3542393177283,  # bf71b21d original (post-N.2: 1769.3542393177286)
            'construction_senior_idc_capitalized': 1552.2292137801358,  # bf71b21d original (post-N.2: 1552.229213780136)
            'construction_senior_commitment_fee': 166.96711785568684,
            'construction_structuring_fee': 471.5143013349264,
            'construction_total_capitalized_financing': 2339.4903869128575,
            'vat_idc': 122.31400101334873,  # bf71b21d original (post-N.2: 122.31400101334872)
            'vat_commitment_fee': 26.465752928759645,  # bf71b21d original (post-N.2: 26.465752928759642)
            'vat_effective_commitment': 3361.5090166666664,
            'vat_peak_requirement': 3361.5090166666664,
            'vat_commitment_mode': 'DERIVED_PEAK_REQUIREMENT',
            'vat_authority': 'TYPED_CONSTRUCTION_VAT_FACILITY_AUTHORITY',
            'final_total_project_uses': 73031.02983135793,
            'final_senior_commitment': 43789.92111682598,
            'outer_iterations': 11,
            'stage_b2_iterations': 8,
            'outer_residual': 1.394391802023165e-08,  # bf71b21d original (post-N.2: 1.394255377817899e-08)
            'final_verification_outer_residual': 6.837126420577988e-10,  # bf71b21d original (post-N.2: 6.834852683823556e-10)
            'hard_project_capex': 70691.53944444444,
            'explicit_financing_cost_uses': 2339.4903869134837,
            'reserve_account_funding': 0.0,
            'other_explicit_project_uses': 0.0,
            'total_project_uses': 73031.02983135793,
            'period_vectors': {
                # bf71b21d originals unavailable (not captured at a clean bf71b21d worktree)
                'senior_idc_accrual': 'UNAVAILABLE_AT_BF71',
                'senior_idc_capitalized_uses': 'UNAVAILABLE_AT_BF71',
                'senior_commitment_fee_accrual': 'UNAVAILABLE_AT_BF71',
                'structuring_fee': 'UNAVAILABLE_AT_BF71',
                'vat_payable': 'UNAVAILABLE_AT_BF71',
                'vat_requirement': 'UNAVAILABLE_AT_BF71',
                'vat_drawn': 'UNAVAILABLE_AT_BF71',
                'vat_undrawn': 'UNAVAILABLE_AT_BF71',
            },
        },
        'shl_first_op_opening': 32261.528269800358,
        'shl_total_interest': 52174.950030124644,
        'shl_total_principal': 42662.17052924682,
        'shl_terminal': 0.0,
        'distributions': 151690.9613741361,
        'sponsor_receipts': 232607.02011878393,
        "period_vectors": {
            # bf71b21d originals unavailable (N.2 ULP cascade overwrote operating
            # schedule hashes before capture; re-running at bf71b21d required)
            'senior_interest': 'UNAVAILABLE_AT_BF71',
            'senior_principal': 'UNAVAILABLE_AT_BF71',
            'senior_ds': 'UNAVAILABLE_AT_BF71',
            'senior_closing': 'UNAVAILABLE_AT_BF71',
            'shl_interest': 'UNAVAILABLE_AT_BF71',
            'shl_principal': 'UNAVAILABLE_AT_BF71',
            'shl_closing': 'UNAVAILABLE_AT_BF71',
        },
    },
}
