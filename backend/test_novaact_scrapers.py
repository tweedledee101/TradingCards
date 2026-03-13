#!/usr/bin/env python3
"""
Test NovaAct Scrapers
Runs PSA and Card Ladder scrapers with mock data to verify webhook integration
"""
import subprocess
import sys
import time

def run_scraper(script_name, description):
    print(f"\n{'='*60}")
    print(f"Running {description}")
    print(f"{'='*60}\n")
    
    try:
        result = subprocess.run(
            [sys.executable, '-m', f'backend.{script_name}'],
            capture_output=False,
            text=True
        )
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error running {script_name}: {e}")
        return False

def main():
    print("🚀 Testing NovaAct Scrapers")
    print("=" * 60)
    print("This will send mock data to your webhook endpoints")
    print("Make sure API server is running: /usr/bin/python3 -m backend.api.run")
    print("=" * 60)
    
    input("\nPress Enter to continue...")
    
    # Run PSA scraper
    psa_success = run_scraper('novaact_psa_template', 'PSA Population Scraper')
    
    time.sleep(2)
    
    # Run Card Ladder scraper
    cl_success = run_scraper('novaact_cardladder_template', 'Card Ladder Price Scraper')
    
    print(f"\n{'='*60}")
    print("Test Results")
    print(f"{'='*60}")
    print(f"PSA Scraper: {'✅ Success' if psa_success else '❌ Failed'}")
    print(f"Card Ladder Scraper: {'✅ Success' if cl_success else '❌ Failed'}")
    print(f"\n{'='*60}")
    print("Next Steps:")
    print("1. Check frontend: http://localhost:3000/card/1")
    print("2. Verify PSA data appears in grading section")
    print("3. Verify price benchmarks appear")
    print("4. Replace mock data with real NovaAct browser automation")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    main()
