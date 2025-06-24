"""
Example usage of the Python-to-SQL Generator
Demonstrates the Platform Primitive in action
"""

import sys
import os
# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.generators.python_to_sql import PythonToSQLGenerator
from app.models.user import User
from app.models.project import Project
from app.models.execution import Execution


def main():
    """Demonstrate the Python-to-SQL generator."""
    print("DevMaster Python-to-SQL Generator Demo")
    print("=" * 50)
    
    generator = PythonToSQLGenerator()
    
    # Generate SQL for individual models
    print("\n1. User Model SQL:")
    print("-" * 30)
    user_sql = generator.generate(User)
    print(user_sql)
    
    print("\n2. Project Model SQL:")
    print("-" * 30)
    project_sql = generator.generate(Project)
    print(project_sql)
    
    print("\n3. Execution Model SQL:")
    print("-" * 30)
    execution_sql = generator.generate(Execution)
    print(execution_sql)
    
    # Generate SQL for all models with proper ordering
    print("\n4. Complete Database Schema:")
    print("-" * 30)
    all_models = [User, Project, Execution]
    complete_sql = generator.generate_multiple(all_models)
    print(complete_sql)
    
    # Save to file
    output_file = "generated_schema.sql"
    with open(output_file, "w") as f:
        f.write(complete_sql)
    print(f"\n✅ Complete schema saved to {output_file}")


if __name__ == "__main__":
    main()
