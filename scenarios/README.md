# Scenarios

Each YAML file is one simulated call. Claude plays the caller using `persona` and `goal`, then a judge scores the
transcript against `success_criteria`. Add or edit scenarios freely; every agent runs the same set, so keep them
general enough for any voice agent (or tag them, see below).

Optional field `applies_to: [team-slug, ...]` limits a scenario to specific teams, for track-specific tests.
