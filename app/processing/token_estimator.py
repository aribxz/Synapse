class TokenEstimator:
    def estimate(self, text):
        return len(text) // 4 # OpenAI's historical benchmark dictates that 1 token is roughly equal to 4 characters of English text.