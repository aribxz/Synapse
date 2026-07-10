# Dealing with Missing Data in Random Forests
Random forests consider two types of missing data: missing data in the original dataset used to create the random forest, and missing data in a new sample that we want to categorize.

## Handling Missing Data in the Original Dataset
The general idea for dealing with missing data in this context is to make an initial guess that could be bad and then gradually refine the guess until it is hopefully a good guess. For categorical variables, the initial guess is the most common value for that variable found in the other samples. For numeric variables, the initial guess is the median value of the variable in the other samples.

## Building a Proximity Matrix
To refine these guesses, we first determine which samples are similar to the one with missing data. We do this by building a random forest and running all of the data down all of the trees. We keep track of similar samples using a proximity matrix, where the proximity value between two samples is the number of trees in which they end up in the same leaf node. We then divide each proximity value by the total number of trees to get a proximity value between 0 and 1.

## RefiningGuesses Using the Proximity Matrix
We use the proximity values for the sample with missing data to make better guesses about the missing values. For categorical variables, we compare the average proximities for each possible value and select the value with the highest average proximity. For numeric variables, we calculate a weighted average of the values of the similar samples, using the proximity values as weights.

## Iterative Refining of Guesses
We repeat the process of building a random forest, running the data down the trees, recalculating the proximities, and refining the guesses until the missing values converge.

## Dealing with Missing Data in New Samples
When we have missing data in a new sample that we want to categorize, we create two copies of the sample, one with each possible value of the missing variable. We then use the iterative method to make a good guess about the missing values. We run the two samples down the trees in the forest and select the one that is correctly labeled by the random forest the most times.

## Visualizing Sample Relationships
The proximity matrix can be used to visualize the relationships between samples. By dividing each proximity value by the total number of trees, we get a distance matrix, where a distance of 0 means the samples are as close as possible, and a distance of 1 means the samples are as far apart as possible. We can use this distance matrix to draw a heat map or an MDS plot, which can be used to show how the samples are related to each other, regardless of the type of data.