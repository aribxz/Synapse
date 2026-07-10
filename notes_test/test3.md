# Dealing with Missing Data in Random Forests
Random forests consider two types of missing data: missing data in the original dataset used to create the random forest, and missing data in a new sample that we want to categorize.

## Missing Data in the Original Dataset
When dealing with missing data in the original dataset, the general idea is to make an initial guess that could be bad and then gradually refine the guess until it is hopefully a good guess. 

### Initial Guess
For categorical variables, the initial guess is the most common value found in the other samples that are similar. For numerical variables, the initial guess is the median value of the similar samples.

### Refining the Guess
To refine the guess, we first determine which samples are similar to the one with missing data. This is done by:

1. Building a random forest
2. Running all of the data down all of the trees
3. Keeping track of similar samples using a proximity matrix

The proximity matrix has a row for each sample and a column for each sample. When two samples end up in the same leaf node, we put a one in the corresponding cell in the proximity matrix.

### Proximity Matrix
We run the data down all the trees and the proximity matrix fills in. Then, we divide each proximity value by the total number of trees.

### Making Better Guesses
We use the proximity values for the sample with missing data to make better guesses about the missing data. For categorical variables, we compare the average proximities for each category and select the one with the higher average proximity. For numerical variables, we use the proximities to calculate a weighted average.

### Iterative Process
We repeat the process of building a random forest, running the data down the trees, recalculating the proximities, and recalculating the missing values until the missing values converge.

## Missing Data in a New Sample
When dealing with missing data in a new sample, we use a similar approach. We create two copies of the new sample, one with each possible value for the missing variable. We then use the iterative method to make a good guess about the missing value. We run the two samples down the trees in the forest and see which one is correctly labeled more often.

## Proximity Matrix Applications
The proximity matrix can be used to create a distance matrix, which can be visualized as a heat map or an MDS plot. This allows us to see the relationships between the samples, regardless of the type of data.

### Distance Matrix
A distance matrix is created by subtracting the proximity values from 1. This matrix can be used to calculate the distance between samples.

### Heat Map and MDS Plot
A heat map and an MDS plot can be created from the distance matrix. These visualizations can help us understand the relationships between the samples.

---
# Key Concepts
* Missing data in the original dataset and in new samples
* Initial guess and refining the guess
* Proximity matrix and distance matrix
* Heat map and MDS plot
* Iterative process for dealing with missing data

# Example Use Case
* Dealing with missing data in a medical dataset
* Creating a random forest model to predict heart disease
* Using the proximity matrix to create a heat map and MDS plot to visualize the relationships between the samples

# Important Notes
* The proximity matrix is a powerful tool for understanding the relationships between samples
* The iterative process can be repeated until the missing values converge
* The distance matrix can be used to create a heat map and MDS plot to visualize the relationships between the samples