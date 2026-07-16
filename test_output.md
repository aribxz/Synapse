# Test Note

At each node the calculation is

$$
a = \phi\!\left(\sum_{i} w_i x_i + b\right)
$$

* x_i – inputs from the previous layer  
* w_i – weight on each incoming connection  
* b – bias term (a constant shift)  
* \phi – activation function (e.g., ReLU, sigmoid, tanh)

`mermaid
flowchart LR
    W[Weighted Sum (z = Σ w·x + b)]
    A[Activation (a = φ(φ (z)))]
    O[Training Time & Compute]
`
*Caption: test diagram*