"""
Computer-generated prompts of various sizes that exercise reasoning capabilities.
"""

# Small prompts (simple reasoning)
SMALL_PROMPTS = [
    "What is the capital of France?",
    "Explain the concept of gravity in simple terms.",
    "What are the first 10 prime numbers?",
    "How do you calculate the area of a circle?",
    "What is the chemical formula for water?",
    "Who wrote 'Romeo and Juliet'?",
    "What is the square root of 144?",
    "Explain the difference between weather and climate.",
    "What is the largest planet in our solar system?",
    "How many continents are there on Earth?"
]

# Medium prompts (moderate reasoning)
MEDIUM_PROMPTS = [
    "Explain the process of photosynthesis and its importance for life on Earth.",
    "Compare and contrast the economic systems of capitalism and socialism.",
    "Describe the causes and consequences of World War I in detail.",
    "How does a blockchain work and what are its main advantages and disadvantages?",
    "Explain the theory of evolution by natural selection with examples.",
    "What are the main differences between classical and quantum mechanics?",
    "Describe the water cycle and its significance for ecosystems.",
    "Explain how vaccines work and why they are important for public health.",
    "What are the key principles of object-oriented programming?",
    "Describe the process of cellular respiration and its role in energy production."
]

# Large prompts (complex reasoning)
LARGE_PROMPTS = [
    """
    You are a historian analyzing the causes of the French Revolution. 
    Provide a comprehensive analysis that includes:
    1. The social and economic conditions in France before the revolution
    2. The role of the Enlightenment in shaping revolutionary ideas
    3. The immediate triggers that led to the outbreak of revolution
    4. The key events during the revolution
    5. The long-term impacts on France and the world
    """,
    """
    As a computer scientist, design a distributed system for a social media platform.
    Your design should address:
    1. System architecture and components
    2. Data storage and retrieval mechanisms
    3. Load balancing and scalability considerations
    4. Fault tolerance and redundancy
    5. Security and privacy measures
    6. Performance optimization strategies
    """,
    """
    You are an economist tasked with analyzing the potential impacts of universal basic income.
    Please provide a detailed analysis that covers:
    1. Economic theories supporting and opposing UBI
    2. Potential effects on employment and labor markets
    3. Impact on poverty and income inequality
    4. Fiscal implications and funding mechanisms
    5. Social and psychological effects on recipients
    6. Comparison with existing welfare systems
    7. Case studies from pilot programs
    """,
    """
    As a medical researcher, explain the current understanding of cancer biology and treatment.
    Your explanation should include:
    1. The molecular and cellular mechanisms of cancer development
    2. The role of genetic and environmental factors
    3. Current diagnostic methods and their limitations
    4. Traditional treatment approaches (surgery, chemotherapy, radiation)
    5. Emerging therapies (immunotherapy, targeted therapy, gene editing)
    6. The concept of personalized medicine in oncology
    7. Current challenges and future directions in cancer research
    """,
    """
    You are a philosopher debating the ethics of artificial intelligence.
    Please provide a comprehensive analysis that addresses:
    1. The ethical implications of creating conscious AI
    2. The potential for AI to develop its own moral framework
    3. The responsibility of creators for AI actions
    4. The impact of AI on employment and social structures
    5. The potential for AI to solve or create ethical dilemmas
    6. The long-term existential risks and benefits of AI development
    7. Proposed ethical frameworks for AI development and deployment
    """
]

# Extra large prompts (very complex reasoning)
XL_PROMPTS = [
    """
    Imagine you are a team of scientists working on a solution to climate change.
    Develop a comprehensive plan that addresses:
    
    Phase 1: Problem Analysis
    - Current state of climate science and projections
    - Main contributors to climate change
    - Regional variations and vulnerabilities
    - Tipping points and irreversible changes
    
    Phase 2: Solution Framework
    - Technological solutions (carbon capture, renewable energy, etc.)
    - Policy and regulatory approaches
    - Economic incentives and market-based solutions
    - Social and behavioral changes
    - International cooperation mechanisms
    
    Phase 3: Implementation Strategy
    - Short-term, medium-term, and long-term action plans
    - Resource allocation and prioritization
    - Stakeholder engagement and public communication
    - Monitoring and evaluation frameworks
    - Adaptive management approaches
    
    Phase 4: Risk Assessment
    - Potential unintended consequences
    - Implementation challenges and barriers
    - Ethical considerations
    - Economic impacts and trade-offs
    - Geopolitical implications
    
    Phase 5: Future Scenarios
    - Best-case, worst-case, and most likely scenarios
    - Timeline for impact assessment
    - Indicators of success or failure
    - Contingency planning
    """,
    """
    You are a futurist tasked with envisioning the next 100 years of human civilization.
    Create a detailed scenario analysis that includes:
    
    Technology:
    - Advances in artificial intelligence and machine learning
    - Breakthroughs in energy production and storage
    - Developments in space exploration and colonization
    - Progress in biotechnology and life extension
    - Evolution of computing and communication technologies
    
    Society:
    - Changes in social structures and family units
    - Evolution of education and work
    - Shifts in cultural norms and values
    - Impact of technology on human relationships
    - Potential new forms of governance
    
    Economy:
    - Transformation of industries and employment
    - New economic models and systems
    - Globalization vs. localization trends
    - Resource allocation and scarcity management
    - Currency and financial system evolution
    
    Environment:
    - Climate change adaptation and mitigation
    - Biodiversity conservation and restoration
    - Resource management and sustainability
    - Human-environment interaction
    - Potential ecological tipping points
    
    Human Evolution:
    - Physical and cognitive enhancements
    - Genetic modification and engineering
    - Human-machine integration
    - Potential new species or post-human evolution
    - Ethical considerations of human enhancement
    
    Challenges:
    - Existential risks to humanity
    - Global cooperation and conflict
    - Inequality and access to technology
    - Preservation of human values and identity
    - Long-term sustainability of civilization
    """
]

# Categorized prompts for easy access
PROMPT_CATEGORIES = {
    'small': SMALL_PROMPTS,
    'medium': MEDIUM_PROMPTS,
    'large': LARGE_PROMPTS,
    'xl': XL_PROMPTS
}

# All prompts combined
ALL_PROMPTS = SMALL_PROMPTS + MEDIUM_PROMPTS + LARGE_PROMPTS + XL_PROMPTS

def get_prompts_by_category(category: str = None):
    """Get prompts by category or all prompts if no category specified."""
    if category and category.lower() in PROMPT_CATEGORIES:
        return PROMPT_CATEGORIES[category.lower()]
    return ALL_PROMPTS

def get_prompt_by_index(index: int):
    """Get a specific prompt by its index."""
    if 0 <= index < len(ALL_PROMPTS):
        return ALL_PROMPTS[index]
    return None

def get_random_prompt(category: str = None):
    """Get a random prompt from a specific category or from all prompts."""
    import random
    prompts = get_prompts_by_category(category)
    return random.choice(prompts) if prompts else None
