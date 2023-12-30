# AgXc/nuke

Nuke native implementations of AgX.

# Content

- [Agx-tonescale.blink](Agx-tonescale.blink) : only the tonescale of AgX as a blink script.

> [!NOTE]
> For the **inset** part of AgX you can check https://github.com/MrLixm/Foundry_Nuke/blob/main/src/primaries_inset

# Usage

## `Agx-tonescale.blink`

The tonescale expect log-encoded data as input. 

The initial formular to calcule the x and y pivot was :

```python
min_EV = -10
max_EV = +6.5
x_pivot = abs(min_EV / (max_EV - min_EV))
# x_pivot = 0.6060606
y_pivot = 0.50
```