# Prototypes for an improved EnergyEnvironment-Class

## Main Goals

+ environments hold >= 1 recordings
- targetConfig must be properly provided with recordings
  - x targets should be mapped to >= x recordings
- solution for mapping 1 Env to > 1 TargetConfig
  - should it just continue?
  - or reuse starting at pos 0?
  - or should a custom mapping be applied?
+ emit warning is single EEnv is used more than once to avoid unwanted correlation effects
  + exception if EEnv allows for it (repetition_ok)
- avoid funky behavior & hidden mechanics


## Secondary Goals / general Improvements

+ add structured metadata (dict) for information about the environment, typical keys would be
  - recording-tool/generation-script,
  - maximum harvestable energy,
  - location (address/GPS),
  - site-description (building/forest),
  - weather,
  - nodes (for each node: transducer, location within experiment, datatype - surface/trace, max-harvestable-energy)
+ dtype, duration, energy_Ws should be kept with EnergyProfile (scalar)
+ duration of EnergyEnvironment (vector) is property/iterator/min(all durations)
+ files get created locally (then copied) or right away in content-directory on server (see prototype 2/3)
+ use overloading (see prototype 2)

## Takeaways

- scalar environment-recordings are now called EnergyProfiles (only temporal dimension)
- EnergyEnvironments now hold >= 1 EnergyProfiles (spatio-temporal)

## Proto 1

### Pros

- allows selecting a single Path or even a slice of a EEnv
  - by EEnv[5] or EEnv[2:5]
-

### Cons

- hidden slightly funky mechanics (slicing EEn)
  - Problem1: [eenv1, eenv2[:]] -> invalid syntax (could be made valid)
  - OK 1:     [eenv1, *eenv2[:]]
  - Problem2: eenv1 + eenv2[:] -> invalid syntax (could be made valid)
  - OK 2:     eemv1[:] + eenv2[:]

## Proto 2

- builds on proto 1

### Pros

- introduces EnergyProfiles (keeps individual data better separated)
- adds addition
- add rudimental checks for mapping (ref-counting)

### Cons

- probably same as proto 1?
  - a bit less, because of addition and breaking everything down into Profiles
- unsolved:
  - merging of metadata when adding

## Proto 3

### Pros

- introduces a chained builder-class

### Cons

- chained setting of firmware (unaware of actual target) is messy (firmware1, firmware2 possible)
- setting other params of TargetConfig is unsolved
