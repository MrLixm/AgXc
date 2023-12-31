# AgXc/nuke

Nuke native implementations of AgX.

# Content

| tool                                                                                                      | description                                      |
|-----------------------------------------------------------------------------------------------------------|--------------------------------------------------|
| [AgXcTonescale.nk](AgXcTonescale.nk)                                                                      | tonescale algorithm of AgX (blink script based). |
| [AgXcDRT.nk](AgXcDRT.nk)                                                                                  | full image rendering pipeline for AgX            |
| [PrimariesInset](https://github.com/MrLixm/Foundry_Nuke/blob/main/src/primaries_inset) (in external repo) | gamut remapping algorithm, referred as "inset"   |


# Instructions

## installation

Common for all tools :

- Open the desired `.nk` file in GitHub or download it locally
- Copy to clipboard the whole content of the nk file
- Paste into any opened Nuke scene

## requirements

As of right now all tools are independent of each others and don't have external dependencies.

* Tools were developed for Nuke15 but MIGHT work on lower versions.
* Tools were developed on Windows but SHOULD work on other platforms.
* Tools use the following nuke features :
  * blink script (compatible with non-commercial version >= 14.0)
  * python for some internal components but static (i.e only triggered on user press)


## `AgXcTonescale.nk`

The tonescale expect log-encoded data as input. 

The initial formula to calcule the x and y pivot specified by Troy was:

```python
min_EV = -10
max_EV = +6.5
x_pivot = abs(min_EV / (max_EV - min_EV))
# >>> x_pivot = 0.6060606
y_pivot = 0.50
```

## `AgXcDRT.nk`

Expect "open domain" data as input, with a `linear BT.2020 D65` encoding.
Output a display-referred result bounds to the specified display that can be directly
previewed or written to disk without any more processing (_example: make sure
the nuke view-transform is disabled when viewing its output_).

### plot

It is possible to visualize a 2D "slice" plot of the process by checking "Show Plot".
A linear 0-1 ramp is being plotted and allow to visualize the effect of the tonescale
and other grading operations.

* The y axis is in [0-1] range and represent pixel "intensity".
* The x axis is a 2D slice of the ramp where lower values represent dark values
of the input and high values the white ones.

### tonescale

"Luminance mapping" of the image with additional grading possibilities to emulate
the color-shift of the analog film print process. Note the process MIGHT actually
have no similarity at all with the film print process but the name was found to be pertinent
and stayed, in lack of better term.

Original AgX implementation applied the tonescale a single time. This one can apply
it 2 times, producing an extra softness that can be comparable to the look
of analog film.

### display

Pick the target display the image should be intended to be displayed on.

# Developer

Check the [src/](src) directory.

# Credits

* Jed Smith: [nuke-colortools](https://github.com/jedypod/nuke-colortools).
* Troy Sobotka: of course for the AgX algorithm