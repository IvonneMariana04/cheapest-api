import { Module } from '@nestjs/common';

import { DatabaseModule } from '../datasources/database.module';

import { TiendaRepository } from './repositories/tienda.repository';
import { repositoryProviders } from './repositories/repository.providers';
import { TiendaService } from './services/tienda.service';

@Module({
  imports: [DatabaseModule],

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