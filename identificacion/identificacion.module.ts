import { Module } from '@nestjs/common';

import { DatabaseModule } from '../datasources/database.module';

import { TiendaRepository } from './repositories/tienda.repository';
import { repositoryProviders } from './repositories/repository.providers';
import { TiendaService } from './services/tienda.service';

import { TiendaController } from './controllers/tienda.controller';

@Module({
  imports: [DatabaseModule],

  controllers: [
    TiendaController,
  ],
  
  providers: [
    ...repositoryProviders,
    TiendaRepository,
    TiendaService,
  ],

  exports: [
    TiendaRepository,
    TiendaService,
  ],
})
export class IdentificacionModule {}