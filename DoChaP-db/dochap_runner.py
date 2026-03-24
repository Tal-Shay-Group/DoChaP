#!/usr/bin/env python3
"""
DoChaP Database Builder Runner
Orchestrates the download and merge stages for building a unified genomic database.

Stages:
  1. Download: Fetch genomic data from NCBI and/or Ensembl
  2. Merge: Integrate NCBI and Ensembl data into a unified SQLite database
"""
import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import shutil
import sys
import argparse
import logging
import sqlite3
from pathlib import Path
from multiprocessing import Pool, cpu_count
from dochap_download import (
    download_ncbi, 
    download_ensembl_gff, 
    fetch_4_way_orthology,
    parse_species_args,
    SpeciesConvention,
    SPECIES_SHORTCUTS
)
from dochap_merge import run_merger
from dochap_definition import DoChaPDB

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def setup_argument_parser():
    """Setup and return the argument parser for the runner."""
    parser = argparse.ArgumentParser(
        description='DoChaP Database Builder - Download and merge genomic data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Pipeline Stages:
  download  - Download genomic data from NCBI and/or Ensembl
  merge     - Merge downloaded data into unified SQLite database
  all       - Run both download and merge stages sequentially

Examples:
  # Download and merge all species
  %(prog)s all -s all -o ./genomic_data
  
  # Download only Human and Mouse from both sources
  %(prog)s download -s H,M -o ./data
  
  # Merge pre-downloaded data for a single species
  %(prog)s merge -s H_sapiens -i ./genomic_data -d human_db.sqlite
  
  # Download all with NCBI only, then merge
  %(prog)s all -s all --source ncbi -o ./data
  
  # Download with shortcuts
  %(prog)s download -s H,M,R,D,X
  
  # Merge multiple species in parallel using 4 cores
  %(prog)s merge -s H,M,R,D,X --cores 4
  
  # Merge multiple species and unify into a single database
  %(prog)s merge -s H,M,R,D,X --unified-db all_species.sqlite
  
  # Download, merge in parallel, and unify
  %(prog)s all -s H,M,R --cores 4 --unified-db vertebrates.sqlite
        """)
    
    parser.add_argument('-stage',
                        choices=['download', 'merge', 'all'],
                        default='all',
                        help='Pipeline stage to run')
    
    parser.add_argument('-s', '--species',
                        default='all',
                        help='Comma-separated list of species. Use shortcuts (H, M, R, D, X) '
                             'or full names (H_sapiens, M_musculus, R_norvegicus, D_rerio, X_tropicalis). '
                             'Examples: "H,M" or "H_sapiens,M_musculus". Default: all')
    
    parser.add_argument('-o', '--download-dir',
                        default='./genomic_data',
                        help='Output directory for downloaded files (default: ./genomic_data)')
    
    parser.add_argument('--source',
                        choices=['ncbi', 'ensembl', 'both'],
                        default='both',
                        help='Data source to download from (default: both) - only for download stage')
    
    parser.add_argument('--no-orthology',
                        dest='fetch_orthology',
                        action='store_false',
                        default=True,
                        help='Skip orthology data fetching (default: fetch when using Ensembl with multiple species)')
    
    parser.add_argument('--skip-download-if-exists',
                        action='store_true',
                        help='Skip downloading if files already exist in output directory')
    
    parser.add_argument('--cores',
                        type=int,
                        default=1,
                        help='Number of CPU cores to use for parallel merge operations (default: 1). '
                             'Use 0 to auto-detect available cores.')
    
    parser.add_argument('--unified-db',
                        default='unified.sqlite',
                        help='Unify all merged species databases into a single database with this name. '
                             'Only applies when merging multiple species. (default: None - keep separate databases)')
    
    parser.add_argument('--keep-individual',
                        action='store_true',
                        help='Keep individual species databases after unification (default: delete them)')
    
    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help='Enable verbose logging')
    
    return parser

def log_header(message):
    logger.info("="*60)
    logger.info(message)
    logger.info("="*60)

def run_download_stage(args, species_list):
    """Run the download stage for specified species."""
    log_header("STAGE 1: DOWNLOAD")
    
    output_path = Path(args.download_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Species to download: {', '.join(species_list)}")
    logger.info(f"Sources: {args.source}")
    logger.info(f"Output directory: {output_path}")
    
    # Download data for each species
    downloaded_species = []
    for species in species_list:
        log_header(f"Downloading {species}")
        try:
            if args.source in ['ncbi', 'both']:
                download_ncbi(species, output_dir= Path(output_path) / species / "refseq")
            if args.source in ['ensembl', 'both']:
                download_ensembl_gff(species, output_dir=Path(output_path) / species / "ensembl")
            downloaded_species.append(species)
            logger.info(f"✓ Successfully downloaded {species}")
        except Exception as e:
            logger.error(f"✗ Failed to download {species}: {e}")
            if not args.skip_download_if_exists:
                raise
    
    # Fetch orthology data
    should_fetch_orthology = (
        args.fetch_orthology and 
        args.source in ['ensembl', 'both'] and 
        len(downloaded_species) > 1
    )
    if should_fetch_orthology:
        log_header("Fetching orthology data")
        try:
            fetch_4_way_orthology()
            logger.info("✓ Successfully fetched orthology data")
        except Exception as e:
            logger.error(f"✗ Failed to fetch orthology data: {e}")
            if not args.skip_download_if_exists:
                raise
    log_header("DOWNLOAD STAGE COMPLETED")
    return downloaded_species


def _merge_single_species(args_tuple):
    """Helper function to merge a single species (for multiprocessing)."""
    input_path, species, db_name = args_tuple
    try:
        run_merger(str(input_path), species, db_name)
        return (species, db_name, None)  # success
    except Exception as e:
        return (species, db_name, str(e))  # failure


def run_merge_stage(args, species_list):
    """Run the merge stage for specified species."""
    log_header("STAGE 2: MERGE")
    
    # Determine input directory
    input_path = Path(args.download_dir) 
    if not input_path.exists():
        logger.error(f"Input directory does not exist: {input_path}")
        sys.exit(1)
    
    # Determine number of cores
    num_cores = args.cores
    if num_cores == 0:
        num_cores = min(cpu_count(), len(species_list))
    elif num_cores > cpu_count():
        logger.warning(f"Requested {num_cores} cores but only {cpu_count()} available. Using {cpu_count()}.")
        num_cores = min(cpu_count(), len(species_list))
    
    # Decide whether to run in parallel
    use_parallel = num_cores > 1 and len(species_list) > 1
    
    logger.info(f"Species to merge: {', '.join(species_list)}")
    logger.info(f"Input directory: {input_path}")
    logger.info(f"Parallel mode: {'Yes' if use_parallel else 'No'} (cores: {num_cores})")
    
    # Prepare merge tasks
    merge_tasks = []
    for species in species_list:
        # Determine output database name
        db_name = f"{species}.sqlite"
        merge_tasks.append((input_path, species, db_name))
    
    merged_databases = []
    failed_species = []
    if use_parallel:
        # Run merges in parallel
        logger.info(f"Starting parallel merge of {len(species_list)} species using {num_cores} cores...")
        with Pool(processes=num_cores) as pool:
            results = pool.map(_merge_single_species, merge_tasks)
        
        # Process results
        for species, db_name, error in results:
            if error is None:
                merged_databases.append(db_name)
                logger.info(f"✓ Successfully created database: {db_name} ({species})")
            else:
                failed_species.append(species)
                logger.error(f"✗ Failed to merge {species}: {error}")
    else:
        # Run merges sequentially
        for input_path, species, db_name in merge_tasks:
            log_header(f"Merging {species}")
            run_merger(str(input_path), species, db_name)
            merged_databases.append(db_name)
            logger.info(f"✓ Successfully created database: {db_name}")
            '''
            try:
                run_merger(str(input_path), species, db_name)
                merged_databases.append(db_name)
                logger.info(f"✓ Successfully created database: {db_name}")
            except FileNotFoundError as e:
                failed_species.append(species)
                logger.error(f"✗ Missing required files for {species}: {e}")
                logger.error(f"  Make sure you've downloaded data for {species} first.")
            except Exception as e:
                failed_species.append(species)
                logger.error(f"✗ Failed to merge {species}: {e}")
            '''
    sys.exit(0)  # TEMPORARY EXIT FOR TESTING
    log_header("MERGE STAGE COMPLETED")
    logger.info(f"Successfully created {len(merged_databases)} database(s):")
    for db in merged_databases:
        logger.info(f"  - {db}")
    
    if failed_species:
        logger.warning(f"Failed to merge {len(failed_species)} species: {', '.join(failed_species)}")
        if not args.skip_download_if_exists:
            raise RuntimeError(f"Failed to merge species: {', '.join(failed_species)}")
    
    # Unify databases if requested and multiple databases were created
    unified_db_path = ''
    if args.unified_db and len(merged_databases) > 1:
        unified_db_path = unify_databases(merged_databases, args.unified_db, args.keep_individual)
    elif args.unified_db and len(merged_databases) == 1:
        logger.warning("Only one database created. Skipping unification (use -d to specify single DB name).")
    
    return merged_databases, unified_db_path


def unify_databases(db_list, output_db_path, keep_individual=False):
    """Unify multiple SQLite databases into a single database.
    
    Args:
        db_list: List of database file paths to unify
        output_db_path: Output unified database path
        keep_individual: If False, delete individual databases after unification
    
    Returns:
        Path to the unified database
    """
    log_header(f"UNIFYING DATABASES")
    logger.info(f"Unifying {len(db_list)} databases into: {output_db_path}")
    
    if os.path.exists(output_db_path):
        logger.warning(f"Unified database {output_db_path} already exists. Removing it.")
        os.remove(output_db_path)
    output_db = DoChaPDB(output_db_path)
    unified_cursor = output_db.cursor
    unified_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = unified_cursor.fetchall()
    
    # Track which database we're processing
    for i, db_path in enumerate(db_list):
        if not os.path.exists(db_path):
            logger.error(f"Database file not found: {db_path}. Skipping.")
            continue
        logger.info(f"  [{i+1}/{len(db_list)}] Attaching {db_path}...")
        try:
            # Attach the database
            db_alias = f"db{i}"
            unified_cursor.execute(f"ATTACH DATABASE '{db_path}' AS {db_alias};")
            for table in tables:
                logger.info(f"    Inserting data into: {table}")
                unified_cursor.execute(f"INSERT OR IGNORE INTO {table} SELECT * FROM {db_alias}.{table};")
            # Detach the database
            unified_cursor.execute(f"DETACH DATABASE {db_alias};")
            logger.info(f"    ✓ Completed {db_path}")
        except sqlite3.Error as e:
            logger.error(f"    ✗ Error processing {db_path}: {e}")
            unified_cursor.execute(f"DETACH DATABASE {db_alias};")
            continue
    
    # Commit and optimize
    logger.info("Committing unified database...")
    output_db.commit()
    
    logger.info("Optimizing unified database...")
    unified_cursor.execute("VACUUM;")
    unified_cursor.execute("ANALYZE;")
    output_db.commit()
    output_db.create_index()
    output_db.close()
    
    # Get database size
    db_size = os.path.getsize(output_db) / (1024 * 1024)  # Size in MB
    logger.info(f"✓ Unified database created: {output_db} ({db_size:.2f} MB)")
    
    # Optionally delete individual databases
    if not keep_individual:
        logger.info("Removing individual species databases...")
        for db_path in db_list:
            if os.path.exists(db_path):
                try:
                    os.remove(db_path)
                    logger.info(f"  - Removed {db_path}")
                except Exception as e:
                    logger.warning(f"  - Failed to remove {db_path}: {e}")
    else:
        logger.info("Keeping individual species databases.")
    
    log_header("UNIFICATION COMPLETED")
    return output_db


def main():
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Parse species
    species_list = parse_species_args(args.species)
    if not species_list:
        logger.error("Error: No valid species specified.")
        sys.exit(1)
    
    # Print pipeline configuration
    log_header("DoChaP Database Builder")
    logger.info(f"Stage: {args.stage}")
    logger.info(f"Species: {', '.join(species_list)}")
    if args.stage in ['merge', 'all']:
        cores_msg = "auto-detect" if args.cores == 0 else str(args.cores)
        logger.info(f"Merge cores: {cores_msg}")
        if not args.unified_db:
            logger.error('Missing unified db file name')
            exit(1)
        logger.info(f"Unified database: {args.unified_db}")
        logger.info(f"Keep individual DBs: {args.keep_individual}")
    
    try:
        # Run appropriate stage(s)
        if args.stage in ['download', 'all']:
            run_download_stage(args, species_list)    
        if args.stage in ['merge', 'all']:
            merged_dbs, unified_db = run_merge_stage(args, species_list)
        log_header("✓ PIPELINE COMPLETED SUCCESSFULLY")    
    except Exception as e:
        logger.error(f"\n\n✗ PIPELINE FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
