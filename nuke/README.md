# AgXc/nuke

Nuke native implementations of AgX.

# Content

- [Agx-tonescale.blink](Agx-tonescale.blink) : only the tonescale of AgX as a blink script.

> [!NOTE]
> For the inset part of AgX you can check https://github.com/MrLixm/Foundry_Nuke/blob/main/src/primaries_inset

# Usage

## `Agx-tonescale.blink`

The tonescale expect log-encoded data as input. Or you can use the `u_log_convert`
option to convert the open-domain input to log internally, or uncheck it and provide
your own implementation.