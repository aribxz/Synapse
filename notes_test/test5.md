# Introduction to Random Forest Part Two
Random forest is a powerful machine learning algorithm that can handle complex data and provide accurate predictions. In this part of our discussion on random forests, we will focus on missing data in sample clustering. Sample clustering is a crucial aspect of random forests, and it is essential to understand how to handle missing data in this context.

## Handling Missing Data in Random Forests
Random forests consider two types of missing data: missing data in the original dataset used to create the random forest, and missing data in a new sample that needs to be categorized. Let's start by exploring how to handle missing data in the original dataset. The general idea is to make an initial guess about the missing value and then refine it until it is accurate.

### Making Initial Guesses
To make an initial guess, we look at the data that is available. For categorical variables, we can use the most common value found in the other samples that are similar to the one with missing data. For example, if we have a patient with missing data for blocked arteries, we can look at the other patients who do not have heart disease and see what the most common value is for blocked arteries. In this case, if the most common value is "no", then our initial guess for the patient with missing data would be "no".

For numeric variables, we can use the median value of the patients who are similar to the one with missing data. For example, if we have a patient with missing data for weight, we can look at the other patients who do not have heart disease and calculate the median weight. This median value would be our initial guess for the patient with missing data.

## Determining Similarity in Random Forests
Once we have made our initial guesses, we need to refine them by determining which samples are similar to the one with missing data. To do this, we use a random forest to identify similar samples. The process involves the following steps:

1. **Build a Random Forest**: We build a random forest using the data with our initial guesses.
2. **Run Data Down Trees**: We run all the data down each tree in the forest. This will give us an idea of which samples end up in the same leaf node, which is a measure of their similarity.
3. **Create a Proximity Matrix**: We create a proximity matrix to keep track of which samples are similar to each other. The proximity matrix has a row for each sample and a column for each sample. If two samples end up in the same leaf node, we put a 1 in the corresponding cell in the proximity matrix.

### Refining Guesses with Proximity Values
Once we have the proximity matrix, we can refine our initial guesses using the proximity values. For categorical variables, we compare the average proximities for each possible value and choose the one with the highest average proximity. For numeric variables, we calculate a weighted average using the proximity values as weights.

We repeat this process several times, refining our guesses until they converge. This means that we build a new random forest, run the data down the trees, and recalculate the proximity matrix and the missing values until the missing values no longer change. This process ensures that our guesses are accurate and reliable.

### Handling Missing Data in New Samples
In addition to handling missing data in the original dataset, we also need to consider how to handle missing data in new samples that need to be categorized. To do this, we create two copies of the new sample, one with each possible value for the missing variable. We then use the iterative method we described earlier to make a good guess about the missing value. Finally, we run the two samples down the trees in the forest and choose the one that is correctly labeled by the random forest. This approach allows us to accurately classify new samples even when there is missing data.